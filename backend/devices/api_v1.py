"""Public open-data API, version 1, following the Polish Standard API (annex 3 to Program otwierania danych 2021–2027).

- JSON:API documents: `data` (resource objects with `type`, `id`, `attributes`, `links`), `links` (`self`, `first`,
  `prev`, `next`, `last`, absolute) and `meta` (total count, data version and date).
- Query conventions of annex 4: `filter[<attribute>]=`, `sort=-a,b`, `fields=a,b` and paging with `page` + `limit`.
  The JSON:API spellings `fields[aeds]=`, `page[number]=` and `page[size]=` are accepted too.
- Errors as in annex 8: `{"errors": [{"error-result", "error-reason", "error-solution", "error-code", "error-help"}]}`,
  where `error-help` links to `/api/v1/errors/{code}`. Unknown parameters, filters, sort keys and fields are a 400.
- `GET /api/v1/version` answers as annex 7 shows; GET and HEAD only; public, no key, no limits.

Mounted at /api/v1 next to the unversioned API the frontend uses (devices/api.py), which is left as it is. Every
answer is built once per data version and query, kept in Redis (devices/cache.py) and served with an ETag."""

import hashlib
import json
import logging
import operator
from datetime import datetime
from functools import reduce, wraps
from math import ceil
from urllib.parse import urlencode

from django.db.models import F, Q
from django.http import Http404, HttpResponse, HttpResponseNotModified, HttpResponsePermanentRedirect
from django.urls import path, re_path
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt
from ninja import Field, NinjaAPI, Schema
from ninja.errors import HttpError, Throttled, ValidationError

from integrations.connectors.common import to_floor
from integrations.models import Integration

from .api import ACCESS, OPERATIONAL_STATUS, PLACEMENT, READINESS, TERYT_PREFIX, _base_url, _etag_matches, with_bbox
from .api import sources as source_rows
from .cache import cached, data_version
from .exports import _data_date, _value, utc_iso
from .models import AdminUnit, Device
from .schema import PUBLISHED_FIELDS as EXPORT_FIELDS  # the open data: no one-line address

logger = logging.getLogger(__name__)

VERSION = {"major": "1", "minor": "0", "patch": "0", "date-mod": "2026-11-22 12:00:00"}
API_VERSION = "{major}.{minor}.{patch}".format(**VERSION)
PREFIX = "/api/v1"
CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_LIMIT, MAX_LIMIT = 50, 500

# The attributes of an `aeds` resource: the reference record (devices/schema.py) without `id`, which JSON:API keeps
# outside `attributes`, plus the municipality name and the last change, as /api/aed/{id} has them
ATTRIBUTES = [f for f in EXPORT_FIELDS if f != "id"] + ["municipality", "updated_at"]
SORTABLE = [
    "id",
    "lat",
    "lon",
    "city",
    "teryt",
    "postal_code",
    "building_name",
    "access",
    "readiness",
    "operational_status",
    "placement",
    "verified_on",
    "last_inspection_on",
    "updated_at",
]
ENUM_FILTERS = {
    "access": ACCESS,
    "readiness": READINESS,
    "operational_status": OPERATIONAL_STATUS,
    "placement": PLACEMENT,
}
FILTERS = ["teryt", "city", *ENUM_FILTERS, "source", "updated_since", "bbox"]
PAGE_KEYS = {"page", "limit", "page[number]", "page[size]"}
FIELD_KEYS = {"fields", "fields[aeds]"}


# ---------------------------------------------------------------- errors

# error-code: (HTTP status, error-result, what it means; served at /api/v1/errors/{code}, the error-help link)
ERRORS = {
    40001: (400, "Nieznany parametr zapytania", "The query has a parameter this resource does not take."),
    40002: (400, "Nieznany filtr", "filter[...] names an attribute that cannot be filtered on."),
    40003: (400, "Nieprawidłowa wartość filtra", "A filter value is empty, malformed or not an allowed value."),
    40004: (400, "Nieobsługiwane sortowanie", "sort names an attribute that cannot be sorted on."),
    40005: (400, "Nieznane pole", "fields names an attribute the resource does not have."),
    40006: (400, "Nieprawidłowe stronicowanie", "page must be a whole number ≥ 1 and limit 1–500."),
    40007: (400, "Nieprawidłowe zapytanie", "A path or query parameter has the wrong type."),
    40401: (404, "Zasób nie istnieje", "No resource at this path in API v1."),
    40402: (404, "Nie znaleziono AED", "No AED with this id; the id comes from /api/v1/aeds."),
    40403: (404, "Nie znaleziono kodu błędu", "No error with this code."),
    40501: (405, "Metoda niedozwolona", "API v1 is read-only: GET and HEAD."),
    41001: (410, "AED nie jest już publikowany", "No source lists this AED any more; it left the dataset."),
    42901: (429, "Przekroczono limit zapytań", "Too many requests. API v1 sets no limits of its own today."),
    50001: (500, "Błąd serwera", "Unexpected server error; try again, and report it if it persists."),
}


class ApiError(Exception):
    def __init__(self, code: int, reason: str, solution: str | None = None):
        super().__init__(reason)
        self.code, self.reason, self.solution = code, reason, solution


def _origin(request) -> str:
    return _base_url(request).rstrip("/")


def error_response(request, code: int, reason: str, solution: str | None = None) -> HttpResponse:
    status, result, _ = ERRORS[code]
    error = {"error-result": result, "error-reason": reason}
    if solution:
        error["error-solution"] = solution
    error |= {"error-code": code, "error-help": f"{_origin(request)}{PREFIX}/errors/{code}", "status": str(status)}
    body = json.dumps({"errors": [error]}, ensure_ascii=False).encode()
    return HttpResponse(body, status=status, content_type=CONTENT_TYPE)


api_v1 = NinjaAPI(
    title="Misja AED — otwarte dane AED, API v1",
    version=API_VERSION,
    description=(
        "Public, read-only open-data API for automated external defibrillators (AED) in Poland, following the "
        "Standard API (annex 3 to Program otwierania danych 2021–2027): JSON:API documents, `filter[...]`, `sort`, "
        "`fields`, `page` + `limit`, navigation links and error objects with `error-result`, `error-reason`, "
        "`error-solution`, `error-code` and `error-help`. No key, no registration, no rate limits. GET and HEAD only."
    ),
    urls_namespace="api-v1",
)


@api_v1.exception_handler(ApiError)
def _api_error(request, exc: ApiError):
    return error_response(request, exc.code, exc.reason, exc.solution)


@api_v1.exception_handler(ValidationError)
def _validation_error(request, exc: ValidationError):
    problems = "; ".join(f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}" for e in exc.errors)
    return error_response(request, 40007, problems or "Invalid request", f"Check the parameters in {PREFIX}/docs.")


@api_v1.exception_handler(Http404)
def _not_found(request, exc):
    return error_response(request, 40401, f"Nie ma zasobu {request.path}", f"Zasoby: {PREFIX}/aeds, {PREFIX}/sources.")


@api_v1.exception_handler(HttpError)
def _http_error(request, exc: HttpError):
    if exc.status_code == 429:
        response = error_response(request, 42901, str(exc.message), "Ponów zapytanie później.")
        if isinstance(exc, Throttled) and exc.wait:
            response["Retry-After"] = str(int(exc.wait))
        return response
    if exc.status_code == 405:
        return error_response(request, 40501, str(exc.message), "Użyj GET lub HEAD.")
    if exc.status_code == 404:
        return error_response(request, 40401, str(exc.message))
    return error_response(request, 40007, str(exc.message))


@api_v1.exception_handler(Exception)
def _server_error(request, exc):
    logger.exception("API v1 error on %s", request.get_full_path())
    return error_response(request, 50001, "Wystąpił nieoczekiwany błąd serwera.", "Spróbuj ponownie za chwilę.")


# ---------------------------------------------------------------- documentation schemas (OpenAPI only)


class ErrorObject(Schema):
    error_result: str = Field(..., alias="error-result", description="What went wrong")
    error_reason: str = Field(..., alias="error-reason", description="Why, for this request")
    error_solution: str | None = Field(None, alias="error-solution", description="How to fix the request")
    error_code: int = Field(..., alias="error-code", description="Provider error code, see /api/v1/errors")
    error_help: str = Field(..., alias="error-help", description="Link to the explanation of the code")
    status: str = Field(..., description="HTTP status code")


class ErrorDocument(Schema):
    errors: list[ErrorObject]


class ResourceObject(Schema):
    type: str
    id: str
    attributes: dict
    links: dict


class CollectionDocument(Schema):
    jsonapi: dict
    data: list[ResourceObject]
    links: dict = Field(..., description="self, first, prev, next, last (absolute URLs; null when there is none)")
    meta: dict = Field(..., description="count, page, limit, pages, data-version, date-mod, api-version")


class ResourceDocument(Schema):
    jsonapi: dict
    data: ResourceObject
    links: dict
    meta: dict


ERROR_RESPONSES = {400: ErrorDocument, 404: ErrorDocument, 405: ErrorDocument, 500: ErrorDocument}
METHODS = ["GET", "HEAD"]


def _param(name: str, description: str, example: str | None = None) -> dict:
    param = {"in": "query", "name": name, "required": False, "schema": {"type": "string"}, "description": description}
    if example:
        param["example"] = example
    return param


FIELDS_PARAMS = [
    _param(
        "fields", f"Comma-separated attributes to return (sparse fieldset): {', '.join(ATTRIBUTES)}", "city,lat,lon"
    ),
    _param("fields[aeds]", "Same as `fields` (JSON:API spelling)"),
]
AEDS_PARAMS = [
    _param("filter[teryt]", "TERYT prefix: 2 digits voivodeship, 4 county, 6 or 7 municipality", "1465011"),
    _param("filter[city]", "Town, exact match ignoring case", "Kraków"),
    *(
        _param(f"filter[{name}]", f"One or more, comma-separated: {', '.join(values)}")
        for name, values in ENUM_FILTERS.items()
    ),
    _param("filter[source]", "Integration slug(s), comma-separated (see /api/v1/sources)", "osm-poland"),
    _param("filter[updated_since]", "ISO 8601 date or moment: AEDs changed after it (no offset = Warsaw time)"),
    _param("filter[bbox]", "minLon,minLat,maxLon,maxLat (WGS84)", "19.79,50.00,20.12,50.12"),
    _param("sort", f"Comma-separated, `-` for descending: {', '.join(SORTABLE)}. Default: id", "-updated_at,id"),
    *FIELDS_PARAMS,
    _param("page", "Page number, from 1", "1"),
    _param("limit", f"Items per page, 1–{MAX_LIMIT} (default {DEFAULT_LIMIT})", "50"),
    _param("page[number]", "Same as `page` (JSON:API spelling)"),
    _param("page[size]", "Same as `limit` (JSON:API spelling)"),
]


# ---------------------------------------------------------------- helpers


def _json_response(request, key: str, build) -> HttpResponse:
    """Serve the document `build()` returns, built once per data version and kept as finished bytes with its MD5."""

    def serialise():
        body = json.dumps(build(), ensure_ascii=False, separators=(",", ":")).encode()
        return hashlib.md5(body).hexdigest(), body  # noqa: S324 — an ETag, not security

    digest, body = cached(f"apiv1:{key}", serialise, timeout=600)
    etag = f'"{digest}"'
    response = (
        HttpResponseNotModified() if _etag_matches(request, etag) else HttpResponse(body, content_type=CONTENT_TYPE)
    )
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=60"
    # Standard techniczny §5: the semantic context of the JSON goes in an HTTP header (JSON-LD 1.1 §6.1)
    response["Link"] = f'<{_origin(request)}/api/v1/context>; rel="{JSONLD_CONTEXT_REL}"; type="application/ld+json"'
    return response


JSONLD_CONTEXT_REL = "http://www.w3.org/ns/json-ld#context"
# Attributes with an obvious schema.org meaning; the rest are terms of this API's own vocabulary (the field
# dictionary at /api/schema describes each one)
SCHEMA_ORG_TERMS = {
    "lat": "latitude",
    "lon": "longitude",
    "building_name": "name",
    "street": "streetAddress",
    "postal_code": "postalCode",
    "city": "addressLocality",
    "opening_hours": "openingHours",
    "photo_url": "image",
    "manufacturer": "manufacturer",
    "model": "model",
    "serial_number": "serialNumber",
    "updated_at": "dateModified",
}


def _query_key(request, *parts) -> str:
    raw = json.dumps([_origin(request), request.path, sorted(request.GET.items()), *parts], ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 — a cache key


def _url(request, path_: str, params: list[tuple[str, str]]) -> str:
    query = urlencode(params, safe="[],:-") if params else ""
    return f"{_origin(request)}{PREFIX}{path_}" + (f"?{query}" if query else "")


def _check_params(request, allowed: set[str], filters: bool = False) -> None:
    for key in request.GET:
        if key in allowed:
            continue
        if filters and key.startswith("filter[") and key.endswith("]"):
            name = key[7:-1]
            if name not in FILTERS:
                raise ApiError(40002, f"Nie można filtrować po „{name}”.", f"Dostępne filtry: {', '.join(FILTERS)}.")
            continue
        listed = ", ".join(sorted(allowed) + (["filter[...]"] if filters else [])) or "none"
        raise ApiError(40001, f"Parametr „{key}” nie jest obsługiwany przez {request.path}.", f"Parametry: {listed}.")


def _parse_fields(request) -> list[str] | None:
    value = request.GET.get("fields[aeds]", request.GET.get("fields"))
    if value is None:
        return None
    fields = [f.strip() for f in value.split(",") if f.strip() and f.strip() != "id"]
    if unknown := [f for f in fields if f not in ATTRIBUTES]:
        raise ApiError(40005, f"Nieznane pola: {', '.join(unknown)}.", f"Dostępne pola: {', '.join(ATTRIBUTES)}.")
    return fields


def _parse_page(request) -> tuple[int, int]:
    def number(keys, default, low, high):
        for key in keys:
            if key in request.GET:
                value = request.GET[key]
                if not value.isdigit() or not low <= int(value) <= (high or int(value)):
                    limit = f"{low}–{high}" if high else f"≥ {low}"
                    raise ApiError(40006, f"{key}={value} jest nieprawidłowe.", f"{key}: liczba całkowita {limit}.")
                return int(value)
        return default

    return number(("page[number]", "page"), 1, 1, None), number(("page[size]", "limit"), DEFAULT_LIMIT, 1, MAX_LIMIT)


def _parse_sort(request) -> list[str]:
    value = request.GET.get("sort")
    if value is None:
        return ["id"]
    keys = [k.strip() for k in value.split(",") if k.strip()]
    if not keys or (unknown := [k for k in keys if k.removeprefix("-") not in SORTABLE]):
        bad = ", ".join(unknown) if keys else "(pusty)"
        raise ApiError(40004, f"Nie można sortować po: {bad}.", f"Sortowanie po: {', '.join(SORTABLE)}; „-” malejąco.")
    return keys


def _filter_value(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise ApiError(40003, f"filter[{name}] jest pusty.", f"Podaj wartość albo pomiń filter[{name}].")
    return value


def _apply_filters(request, qs):
    for key, raw in request.GET.items():
        if not key.startswith("filter["):
            continue
        name, value = key[7:-1], _filter_value(key[7:-1], raw)
        if name == "teryt":
            if not TERYT_PREFIX.fullmatch(value):
                raise ApiError(40003, f"filter[teryt]={value} nie jest kodem TERYT.", "2, 4, 6 lub 7 cyfr, np. 14.")
            qs = qs.filter(teryt__startswith=value)
        elif name == "city":
            qs = qs.filter(city__iexact=value)
        elif name in ENUM_FILTERS:
            wanted = [v.strip() for v in value.split(",") if v.strip()]
            if bad := [v for v in wanted if v not in ENUM_FILTERS[name]]:
                allowed = ", ".join(ENUM_FILTERS[name])
                raise ApiError(40003, f"filter[{name}]: nieznana wartość {', '.join(bad)}.", f"Dozwolone: {allowed}.")
            qs = qs.filter(**{f"{name}__in": wanted})
        elif name == "source":
            wanted = [v.strip() for v in value.split(",") if v.strip()]
            known = set(Integration.objects.values_list("slug", flat=True))
            if bad := [v for v in wanted if v not in known]:
                raise ApiError(
                    40003, f"filter[source]: nieznane źródło {', '.join(bad)}.", f"Źródła: {', '.join(sorted(known))}."
                )
            qs = qs.filter(reduce(operator.or_, (Q(sources__contains=[slug]) for slug in wanted)))
        elif name == "updated_since":
            moment = parse_datetime(value)
            if moment is None and (day := parse_date(value)):
                moment = datetime(day.year, day.month, day.day)
            if moment is None:
                raise ApiError(40003, f"filter[updated_since]={value} nie jest datą ISO 8601.", "Np. 2026-11-20.")
            qs = qs.filter(updated_at__gt=timezone.make_aware(moment) if timezone.is_naive(moment) else moment)
        elif name == "bbox":
            qs = with_bbox(qs, _check_bbox(value))
    return qs


def _check_bbox(value: str) -> str:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(x) for x in value.split(","))
        valid = -180 <= min_lon <= max_lon <= 180 and -90 <= min_lat <= max_lat <= 90
    except ValueError:
        valid = False
    if not valid:
        raise ApiError(
            40003,
            f"filter[bbox]={value} nie jest prostokątem.",
            "minLon,minLat,maxLon,maxLat w WGS84, np. 19.79,50,20.12,50.12.",
        )
    return value


def _municipalities(devices) -> dict[str, str]:
    teryts = {d.teryt for d in devices if d.teryt}
    return dict(AdminUnit.objects.filter(teryt__in=teryts).values_list("teryt", "municipality")) if teryts else {}


def aed_resource(request, device: Device, municipality: str | None, fields: list[str] | None) -> dict:
    """An `aeds` resource object: the reference record with the values the exports use (devices/exports.py)."""
    attributes = {f: _value(getattr(device, f)) for f in EXPORT_FIELDS if f != "id"}
    attributes["floor"] = to_floor(device.floor)
    attributes["municipality"] = municipality
    attributes["updated_at"] = _value(device.updated_at)
    if fields is not None:
        attributes = {k: v for k, v in attributes.items() if k in fields}
    return {
        "type": "aeds",
        "id": device.pk,
        "attributes": attributes,
        "links": {"self": f"{_origin(request)}{PREFIX}/aeds/{device.pk}"},
    }


def _meta(**extra) -> dict:
    return extra | {"data-version": data_version(), "date-mod": utc_iso(_data_date()), "api-version": API_VERSION}


JSONAPI = {"version": "1.0"}


# ---------------------------------------------------------------- resources


@api_v1.api_operation(
    METHODS,
    "/aeds",
    response={200: CollectionDocument, **ERROR_RESPONSES},
    tags=["aeds"],
    summary="AEDs (collection)",
    openapi_extra={"parameters": AEDS_PARAMS},
)
def aeds(request):
    """Active AEDs of the merged nationwide dataset as JSON:API resources (`type: aeds`), filtered, sorted and paged.
    Example: `/api/v1/aeds?filter[teryt]=12&filter[access]=public&sort=-updated_at&fields=city,lat,lon&page=2&limit=100`.
    """
    _check_params(request, {"sort"} | PAGE_KEYS | FIELD_KEYS, filters=True)
    fields, (page, limit), sort = _parse_fields(request), _parse_page(request), _parse_sort(request)
    qs = _apply_filters(request, Device.objects.filter(active=True, merged_into__isnull=True))
    order = [
        F(k.removeprefix("-")).desc(nulls_last=True) if k.startswith("-") else F(k).asc(nulls_last=True) for k in sort
    ]
    if not any(k.removeprefix("-") == "id" for k in sort):
        order.append(F("id").asc())
    qs = qs.order_by(*order)
    kept = sorted((k, v) for k, v in request.GET.items() if k not in PAGE_KEYS)

    def build():
        count = qs.count()
        pages = max(1, ceil(count / limit))
        devices = list(qs[(page - 1) * limit : page * limit])
        municipalities = _municipalities(devices)

        def link(number):
            return _url(request, "/aeds", [*kept, ("page", str(number)), ("limit", str(limit))])

        return {
            "jsonapi": JSONAPI,
            "data": [aed_resource(request, d, municipalities.get(d.teryt), fields) for d in devices],
            "links": {
                "self": link(page),
                "first": link(1),
                "prev": link(min(page - 1, pages)) if page > 1 else None,
                "next": link(page + 1) if page < pages else None,
                "last": link(pages),
            },
            "meta": _meta(count=count, page=page, limit=limit, pages=pages),
        }

    return _json_response(request, f"aeds:{_query_key(request, page, limit)}", build)


@api_v1.api_operation(
    METHODS,
    "/aeds/{aed_id}",
    response={200: ResourceDocument, 410: ErrorDocument, **ERROR_RESPONSES},
    tags=["aeds"],
    summary="One AED",
    openapi_extra={
        "parameters": [
            {
                "in": "path",
                "name": "aed_id",
                "required": True,
                "schema": {"type": "string"},
                "example": "AED-PL-1A2B3C",
            },
            *FIELDS_PARAMS,
        ]
    },
)
def aed(request, aed_id: str):
    """One AED. A duplicate merged into another answers 301 to that one; an AED no source lists any more answers 410."""
    _check_params(request, FIELD_KEYS)
    fields = _parse_fields(request)

    def outcome():
        device = Device.objects.filter(pk=aed_id).first()
        if device is None:
            return "missing", None
        if device.merged_into_id:
            return "merged", device.merged_into_id
        if not device.active:
            return "gone", None
        return "ok", None

    state, target = cached(f"apiv1:aed-state:{aed_id}", outcome, timeout=600)
    if state == "missing":
        raise ApiError(40402, f"Nie ma AED o id {aed_id}.", f"Identyfikatory zwraca {PREFIX}/aeds.")
    if state == "gone":
        raise ApiError(41001, f"AED {aed_id} nie występuje już w żadnym źródle.", f"Aktualne dane: {PREFIX}/aeds.")
    if state == "merged":
        return HttpResponsePermanentRedirect(_url(request, f"/aeds/{target}", sorted(request.GET.items())))

    def build():
        device = Device.objects.get(pk=aed_id)
        return {
            "jsonapi": JSONAPI,
            "data": aed_resource(request, device, _municipalities([device]).get(device.teryt), fields),
            "links": {"self": _url(request, f"/aeds/{aed_id}", sorted(request.GET.items()))},
            "meta": _meta(),
        }

    return _json_response(request, f"aed:{_query_key(request)}", build)


@api_v1.api_operation(
    METHODS, "/sources", response={200: CollectionDocument, **ERROR_RESPONSES}, tags=["sources"], summary="Sources"
)
def sources(request):
    """The sources merged into the dataset (`type: sources`, id = integration slug), each linking to its AEDs."""
    _check_params(request, set())

    def build():
        rows = source_rows(request)
        self_link = _url(request, "/sources", [])
        return {
            "jsonapi": JSONAPI,
            "data": [
                {
                    "type": "sources",
                    "id": row["slug"],
                    "attributes": {k: v for k, v in row.items() if k != "slug"},
                    "links": {"aeds": _url(request, "/aeds", [("filter[source]", row["slug"])])},
                }
                for row in rows
            ],
            "links": {"self": self_link, "first": self_link, "prev": None, "next": None, "last": self_link},
            "meta": _meta(count=len(rows)),
        }

    return _json_response(request, f"sources:{_query_key(request)}", build)


@api_v1.api_operation(METHODS, "/version", response={200: dict, **ERROR_RESPONSES}, tags=["meta"], summary="Version")
def version(request):
    """The API version (SemVer; only MAJOR selects it, in the path /api/v1) as annex 7 of the Standard API shows."""
    _check_params(request, set())

    def build():
        return {
            "api-version": VERSION,
            "links": {
                "self": _url(request, "/version", []),
                "docs": _url(request, "/docs", []),
                "openapi": _url(request, "/openapi.json", []),
            },
            "meta": _meta(),
        }

    return _json_response(request, f"version:{_query_key(request)}", build)


@api_v1.api_operation(METHODS, "/context", response={200: dict, **ERROR_RESPONSES}, tags=["meta"], summary="Context")
def context(request):
    """JSON-LD context for the attributes of an AED: schema.org where a term matches, this API's vocabulary
    otherwise. Every response announces it in its Link header."""
    _check_params(request, set())

    def build():
        origin = _origin(request)
        terms = {name: f"https://schema.org/{term}" for name, term in SCHEMA_ORG_TERMS.items()}
        return {
            "@context": {
                "@vocab": f"{origin}/api/schema#",
                "schema": "https://schema.org/",
                "aeds": "schema:Place",
                **terms,
                "updated_at": {"@id": "https://schema.org/dateModified", "@type": "schema:DateTime"},
            }
        }

    return _json_response(request, f"context:{_query_key(request)}", build)


def _error_resource(request, code: int) -> dict:
    status, result, description = ERRORS[code]
    return {
        "type": "errors",
        "id": str(code),
        "attributes": {"status": status, "error-result": result, "description": description},
        "links": {"self": _url(request, f"/errors/{code}", [])},
    }


@api_v1.api_operation(
    METHODS, "/errors", response={200: CollectionDocument, **ERROR_RESPONSES}, tags=["meta"], summary="Error codes"
)
def errors(request):
    """Every `error-code` this API answers with: HTTP status, `error-result` and what it means."""
    _check_params(request, set())

    def build():
        self_link = _url(request, "/errors", [])
        return {
            "jsonapi": JSONAPI,
            "data": [_error_resource(request, code) for code in ERRORS],
            "links": {"self": self_link, "first": self_link, "prev": None, "next": None, "last": self_link},
            "meta": {"count": len(ERRORS), "api-version": API_VERSION},
        }

    return _json_response(request, f"errors:{_query_key(request)}", build)


@api_v1.api_operation(
    METHODS, "/errors/{code}", response={200: ResourceDocument, **ERROR_RESPONSES}, tags=["meta"], summary="Error code"
)
def error_code(request, code: str):
    """One `error-code`: the page each error's `error-help` links to."""
    _check_params(request, set())
    if not code.isdigit() or int(code) not in ERRORS:
        raise ApiError(40403, f"Nie ma kodu błędu {code}.", f"Kody błędów: {PREFIX}/errors.")
    resource = _error_resource(request, int(code))
    body = {"jsonapi": JSONAPI, "data": resource, "links": {"self": resource["links"]["self"]}}
    return _json_response(request, f"error:{_query_key(request)}", lambda: body)


# ---------------------------------------------------------------- entry point, unknown paths, 405


@csrf_exempt
def index(request):
    """`/api/v1`: what the API offers, its limits (none) and where the documentation is (Standard API §4)."""
    if request.method not in METHODS:
        return _method_not_allowed(request, ", ".join(METHODS))
    try:
        _check_params(request, set())
    except ApiError as exc:
        return error_response(request, exc.code, exc.reason, exc.solution)

    def build():
        return {
            "meta": {
                "title": "Misja AED — otwarte dane AED w Polsce, API v1",
                "description": (
                    "Zbiorcza, ogólnopolska baza defibrylatorów AED z wielu źródeł. Dostęp anonimowy, bez klucza i "
                    "rejestracji, bez limitów zapytań. Tylko GET i HEAD, odpowiedzi w JSON (JSON:API)."
                ),
                "limits": "none",
                "authentication": "none",
                "api-version": API_VERSION,
            },
            "links": {
                "self": _url(request, "", []),
                "aeds": _url(request, "/aeds", []),
                "sources": _url(request, "/sources", []),
                "version": _url(request, "/version", []),
                "errors": _url(request, "/errors", []),
                "docs": _url(request, "/docs", []),
                "openapi": _url(request, "/openapi.json", []),
            },
        }

    return _json_response(request, f"index:{_origin(request)}", build)


@csrf_exempt
def not_found(request, *args, **kwargs):
    hint = " Usuń ukośnik na końcu adresu." if request.path.endswith("/") and request.path != f"{PREFIX}/" else ""
    return error_response(
        request,
        40401,
        f"Nie ma zasobu {request.path}.{hint}",
        f"Zasoby: {PREFIX}/aeds, {PREFIX}/aeds/{{id}}, {PREFIX}/sources, {PREFIX}/version; dokumentacja: {PREFIX}/docs.",
    )


def _method_not_allowed(request, allowed: str) -> HttpResponse:
    response = error_response(
        request, 40501, f"Metoda {request.method} nie jest obsługiwana dla {request.path}.", f"Użyj: {allowed}."
    )
    response["Allow"] = allowed
    return response


def _with_error_format(view):
    """Ninja answers an unsupported method with a plain-text 405; give it the standard's error body."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        if response.status_code == 405 and not response.get("Content-Type", "").startswith("application/json"):
            return _method_not_allowed(request, response.get("Allow", ", ".join(METHODS)))
        return response

    return wrapper


def _urls():
    patterns, app_name, namespace = api_v1.urls
    for pattern in patterns:
        if hasattr(pattern, "callback"):
            pattern.callback = _with_error_format(pattern.callback)
    return patterns, app_name, namespace


# Included by config/urls.py before the unversioned /api/
urlpatterns = [
    re_path(r"^api/v1/?$", index),
    path("api/v1/", _urls()),
    re_path(r"^api/v1/", not_found),
]
