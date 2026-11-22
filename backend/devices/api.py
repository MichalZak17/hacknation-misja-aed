"""Public open-data API (devices, stats, sources, exports) and the admin endpoints that act on devices (merge review,
maintenance events). Read endpoints are cached in Redis per data version."""

import gzip
import hashlib
import json
import re
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import connection
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseNotModified, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router, Schema
from ninja.security import django_auth

from integrations.models import Integration, SourceRecord

from . import boundaries, regions
from .availability import availability
from .cache import bump_data_version, cached, data_version
from .coverage import coverage
from .exports import CONTENT_TYPES, get_dataset, get_export, get_harvester_xml
from .merge import accept_match, recompute
from .models import Device, MaintenanceEvent, MatchCandidate
from .nearest import (
    DEMO_AED,
    DEMO_ID,
    find_nearby,
    find_nearest,
    haversine_m,
    links,
    nearest_response,
    public_record,
)
from .schema import EXPORT_FIELDS, schema_dicts

public = Router(tags=["open data"])
admin = Router(tags=["devices (admin)"], auth=django_auth)

READINESS = ["ready", "attention", "expired", "unknown"]
ACCESS = ["public", "limited", "private", "unknown"]
PLACEMENT = ["inside_building", "outside_on_building", "freestanding_outdoor", "vehicle", "unknown"]
OPERATIONAL_STATUS = ["operational", "out_of_service", "missing", "decommissioned", "unknown"]
# Query defaults of a datetime type live here (ruff B008 treats them as mutable calls in a signature)
UPDATED_SINCE = Query(None, description="Only devices changed after this ISO 8601 moment")
SINCE = Query(..., description="ISO 8601 moment; store `as_of` from the answer for the next call")
TERYT_PREFIX = re.compile(r"\d{2}|\d{4}|\d{6}|\d{7}")
DETAIL_EXTRA = ["merged_into_id", "created_at", "updated_at"]


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _aware(value: datetime | None) -> datetime | None:
    """A query datetime without an offset is Polish local time."""
    return timezone.make_aware(value) if value is not None and timezone.is_naive(value) else value


def list_item(device: Device) -> dict:
    return {
        "id": device.id,
        "lat": device.lat,
        "lon": device.lon,
        "name": device.building_name,
        "address": device.address,
        "city": device.city,
        "access": device.access,
        "readiness": device.readiness,
        "operational_status": device.operational_status,
        "active": device.active,
        "source_count": device.source_count,
        "sources": device.sources,
        "verified_on": _iso(device.verified_on),
    }


def parse_bbox(bbox: str | None):
    if not bbox:
        return None
    try:
        min_lon, min_lat, max_lon, max_lat = (float(x) for x in bbox.split(","))
    except ValueError:
        return None
    return min_lon, min_lat, max_lon, max_lat


def with_bbox(queryset, bbox):
    box = parse_bbox(bbox)
    if not box:
        return queryset
    # geography && envelope uses the GiST index on geom
    return queryset.extra(where=["geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)::geography"], params=list(box))


# ---------------------------------------------------------------- public


@public.get("/stats")
def stats(request):
    def build():
        devices = Device.objects.filter(merged_into__isnull=True)
        active = devices.filter(active=True)
        by_readiness = dict.fromkeys(READINESS, 0) | {
            r["readiness"]: r["n"] for r in active.values("readiness").annotate(n=Count("id"))
        }
        by_access = dict.fromkeys(ACCESS, 0) | {
            r["access"]: r["n"] for r in active.values("access").annotate(n=Count("id"))
        }
        sources = []
        for integration in Integration.objects.annotate(
            n=Count("records", filter=Q(records__removed_at__isnull=True)),
            valid=Count("records", filter=Q(records__removed_at__isnull=True, records__is_valid=True)),
        ):
            sources.append(
                {
                    "slug": integration.slug,
                    "name": integration.name,
                    "records": integration.n,
                    "valid_records": integration.valid,
                    "last_success_at": _iso(integration.last_success_at),
                }
            )
        maintenance = (
            Q(pads_expiry_date__isnull=False)
            | Q(battery_expiry_date__isnull=False)
            | Q(last_inspection_on__isnull=False)
            | Q(serial_number__isnull=False)
        )
        # The brief's question, field by field: where is it, can I get to it now, does it work
        completeness = active.aggregate(
            address=Count("id", filter=~Q(address__isnull=True) & ~Q(address="")),
            location_detail=Count(
                "id",
                filter=(~Q(location_detail__isnull=True) & ~Q(location_detail=""))
                | (~Q(building_name__isnull=True) & ~Q(building_name="")),
            ),
            access_known=Count("id", filter=~Q(access="unknown")),
            opening_hours=Count("id", filter=~Q(opening_hours__isnull=True) & ~Q(opening_hours="")),
            maintenance=Count("id", filter=maintenance),
            verified=Count("id", filter=Q(verified_on__isnull=False)),
            operator=Count("id", filter=~Q(operator_name__isnull=True) & ~Q(operator_name="")),
            photo=Count("id", filter=Q(photo_url__isnull=False)),
        )
        today = timezone.localdate()
        year_ago, three_years_ago = today - timedelta(days=365), today - timedelta(days=3 * 365)
        verification_age = active.aggregate(
            last_year=Count("id", filter=Q(verified_on__gte=year_ago)),
            one_to_three_years=Count("id", filter=Q(verified_on__lt=year_ago, verified_on__gte=three_years_ago)),
            older=Count("id", filter=Q(verified_on__lt=three_years_ago)),
            never=Count("id", filter=Q(verified_on__isnull=True)),
        )
        by_source_count = active.aggregate(
            one=Count("id", filter=Q(source_count__lte=1)),
            two=Count("id", filter=Q(source_count=2)),
            three_or_more=Count("id", filter=Q(source_count__gte=3)),
        )
        return {
            "devices": devices.count(),
            "active_devices": active.count(),
            "completeness": completeness,
            "by_readiness": by_readiness,
            "by_access": by_access,
            "by_placement": dict.fromkeys(PLACEMENT, 0)
            | {r["placement"]: r["n"] for r in active.values("placement").annotate(n=Count("id"))},
            "verification_age": verification_age,
            "by_source_count": by_source_count,
            "with_maintenance_data": active.filter(maintenance).count(),
            "multi_source": active.filter(source_count__gt=1).count(),
            "pending_matches": MatchCandidate.objects.filter(status="pending").count(),
            "sources": sources,
            "data_version": data_version(),
            "generated_at": timezone.now().isoformat(),
        }

    return cached("stats", build, timeout=300)


class Detail(Schema):
    detail: str


@public.get("/stats/regions", response={200: dict, 400: Detail})
def stats_regions(
    request,
    level: str = Query("voivodeship", description="voivodeship (16 rows) or municipality (gmina, ~2,480 rows)"),
    voivodeship: str | None = Query(None, description="Two-digit TERYT code: only units in this voivodeship"),
):
    """AED coverage per voivodeship or municipality: active devices, by access, open 24/7, verified, area (PRG) and
    devices per 100 km². Units with no AED are listed with devices 0, so the gaps show."""
    if level not in regions.LEVELS:
        return 400, {"detail": f"Unknown level {level}; use {', '.join(regions.LEVELS)}"}
    if voivodeship is not None and voivodeship not in regions.VOIVODESHIPS:
        return 400, {"detail": f"Unknown voivodeship {voivodeship}; use a two-digit TERYT code (02, 04 … 32)"}

    def build():
        return {
            "level": level,
            "voivodeship": voivodeship,
            "items": regions.regions(level, voivodeship),
            "unlocated": regions.unlocated(),
            "data_version": data_version(),
            "generated_at": timezone.now().isoformat(),
        }

    return cached(f"regions:{level}:{voivodeship}", build)


@public.get("/sources")
def sources(request):
    def build():
        rows = []
        for i in Integration.objects.filter(enabled=True).annotate(
            n=Count("records", filter=Q(records__removed_at__isnull=True, records__is_valid=True))
        ):
            rows.append(
                {
                    "slug": i.slug,
                    "name": i.name,
                    "publisher": i.publisher,
                    "source_url": i.source_url,
                    "homepage_url": i.homepage_url,
                    "attribution": i.attribution,
                    "records": i.n,
                    "last_success_at": _iso(i.last_success_at),
                }
            )
        return rows

    return cached("sources", build)


@public.get("/sources/coverage")
def sources_coverage(request):
    """Reference scope per source: for each field of the reference record, how many of each source's live records
    state it (count, %), and how much of the merged dataset has it, broken down by source and method."""
    return cached("sources-coverage", coverage)


@public.get("/schema")
def schema(request):
    return schema_dicts()


@public.get("/devices", response={200: dict, 400: Detail})
def devices(
    request,
    q: str | None = Query(None, description="Text in the id, name, address, city, serial number, location or operator"),
    readiness: str | None = Query(None, description="ready, attention, expired, unknown"),
    access: str | None = Query(None, description="public, limited, private, unknown"),
    source: str | None = Query(None, description="Integration slug, e.g. osm-poland"),
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat (WGS84)"),
    teryt: str | None = Query(
        None, description="TERYT prefix: 2 digits voivodeship, 4 county, 6 or 7 municipality (e.g. 1465011 Warszawa)"
    ),
    city: str | None = Query(None, description="Town, exact match ignoring case"),
    placement: str | None = Query(None, description=", ".join(PLACEMENT)),
    operational_status: str | None = Query(None, description=", ".join(OPERATIONAL_STATUS)),
    open_24_7: bool | None = Query(None, description="true: only AEDs with opening_hours 24/7; false: all others"),
    updated_since: datetime | None = UPDATED_SINCE,
    active: bool = True,
    limit: int = 50,
    offset: int = 0,
):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    if teryt and not TERYT_PREFIX.fullmatch(teryt):
        return 400, {"detail": "teryt must be 2, 4, 6 or 7 digits (voivodeship, county, municipality)"}
    for name, value, allowed in (
        ("readiness", readiness, READINESS),
        ("access", access, ACCESS),
        ("placement", placement, PLACEMENT),
        ("operational_status", operational_status, OPERATIONAL_STATUS),
    ):
        if value and value not in allowed:
            return 400, {"detail": f"Unknown {name} {value}; use {', '.join(allowed)}"}

    def build():
        qs = Device.objects.filter(merged_into__isnull=True)
        if active:
            qs = qs.filter(active=True)
        if readiness:
            qs = qs.filter(readiness=readiness)
        if access:
            qs = qs.filter(access=access)
        if source:
            qs = qs.filter(sources__contains=[source])
        if teryt:
            qs = qs.filter(teryt__startswith=teryt)
        if city:
            qs = qs.filter(city__iexact=city.strip())
        if placement:
            qs = qs.filter(placement=placement)
        if operational_status:
            qs = qs.filter(operational_status=operational_status)
        if open_24_7 is not None:
            qs = qs.filter(opening_hours="24/7") if open_24_7 else qs.exclude(opening_hours="24/7")
        if updated_since:
            qs = qs.filter(updated_at__gt=updated_since)
        if q:
            term = q.strip()
            qs = qs.filter(
                Q(id__icontains=term)
                | Q(building_name__icontains=term)
                | Q(address__icontains=term)
                | Q(city__icontains=term)
                | Q(serial_number__icontains=term)
                | Q(location_detail__icontains=term)
                | Q(operator_name__icontains=term)
            )
        qs = with_bbox(qs, bbox).order_by("id")
        return {"count": qs.count(), "items": [list_item(d) for d in qs[offset : offset + limit]]}

    updated_since = _aware(updated_since)
    since = updated_since.isoformat() if updated_since else None
    key = (
        f"devices:{q}:{readiness}:{access}:{source}:{bbox}:{teryt}:{city}:{placement}:{operational_status}:"
        f"{open_24_7}:{since}:{active}:{limit}:{offset}"
    )
    return cached(key, build, timeout=600)


def _etag_matches(request, etag: str) -> bool:
    candidates = request.headers.get("If-None-Match", "").split(",")
    return any(c.strip().removeprefix("W/") in (etag, "*") for c in candidates)


@public.get("/devices/points")
def points(request, bbox: str | None = None):
    """Every active device for the map (~3.5 MB of JSON nationwide). Built once per data version as finished bytes,
    raw and gzipped, so a request costs no serialising or compressing. ETag + no-cache: the browser revalidates and
    gets a 304 until the data changes, and the map's worker reuses the copy the page prefetched."""

    def build():
        qs = with_bbox(Device.objects.filter(active=True), bbox)
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                "properties": {"id": id_, "readiness": readiness, "access": access, "sources": count},
            }
            for id_, lon, lat, readiness, access, count in qs.values_list(
                "id", "lon", "lat", "readiness", "access", "source_count"
            ).iterator(chunk_size=5000)
        ]
        body = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")).encode()
        return hashlib.md5(body).hexdigest(), body, gzip.compress(body, compresslevel=9, mtime=0)

    digest, body, gzipped = cached(f"points-bytes:{bbox}", build, timeout=None)
    use_gzip = bool(re.search(r"\bgzip\b", request.headers.get("Accept-Encoding", "")))
    # One strong ETag per encoding: the two bodies differ byte for byte
    etag = f'"{digest}-gz"' if use_gzip else f'"{digest}"'
    if _etag_matches(request, etag):
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(gzipped if use_gzip else body, content_type="application/json")
        if use_gzip:
            response["Content-Encoding"] = "gzip"  # GZipMiddleware leaves an encoded response alone
    response["ETag"] = etag
    response["Cache-Control"] = "no-cache"
    response["Vary"] = "Accept-Encoding"
    return response


@public.get("/devices/nearest")
def nearest(request, lat: float, lon: float, limit: int = 5):
    limit = max(1, min(limit, 50))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, ST_Distance(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography)
            FROM devices_device WHERE active
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
            LIMIT %(limit)s
            """,
            {"lat": lat, "lon": lon, "limit": limit},
        )
        distances = dict(cursor.fetchall())
    found = {d.id: d for d in Device.objects.filter(id__in=distances)}
    return [list_item(found[i]) | {"distance_m": round(distances[i], 1)} for i in distances if i in found]


NearestError = Detail

OPEN_NOW = Query(False, description="Only AEDs whose opening hours cover the moment (now, or `at`)")
AT = Query(None, description="Evaluate availability at this ISO 8601 moment instead of now (local time: Warsaw)")


def _parse_access(access: str | None):
    """(wanted access values or None, error message or None)."""
    wanted = [a.strip() for a in access.split(",") if a.strip()] if access else None
    if wanted and (bad := sorted(set(wanted) - set(ACCESS))):
        return None, f"Unknown access value {', '.join(bad)}; use {', '.join(ACCESS)}"
    return wanted, None


@public.get("/aed/nearest", response={200: dict, 400: NearestError, 404: NearestError})
def nearest_aed(
    request,
    lat: float = Query(..., ge=-90, le=90, description="Your latitude, WGS84 (e.g. 52.2297)"),
    lon: float = Query(..., ge=-180, le=180, description="Your longitude, WGS84 (e.g. 21.0122)"),
    access: str | None = Query(None, description="Comma-separated: public, limited, private, unknown"),
    max_distance_m: float | None = Query(None, gt=0, le=100_000, description="Search radius in metres"),
    open_now: bool = OPEN_NOW,
    at: datetime | None = AT,
    demo: bool = Query(False, description="Answer with the demo AED that has every field filled"),
):
    """The single nearest AED a rescuer can use: every field of the reference record, the distance in metres, whether
    its opening hours cover this moment, and links to a map and walking directions. Skips AEDs in vehicles and ones
    reported out of service, missing or decommissioned."""
    if demo:
        return nearest_response(
            DEMO_AED, haversine_m(lat, lon, DEMO_AED.lat, DEMO_AED.lon), lat, lon, _base_url(request), at
        )
    wanted, error = _parse_access(access)
    if error:
        return 400, {"detail": error}
    found = find_nearest(lat, lon, wanted, max_distance_m, (at or timezone.now()) if open_now else None)
    if not found:
        radius = f" within {max_distance_m:g} m" if max_distance_m else ""
        open_ = " open at that moment" if open_now else ""
        return 404, {"detail": f"No AED{open_} found{radius} of {lat}, {lon}"}
    device, distance = found
    return nearest_response(device, distance, lat, lon, _base_url(request), at)


@public.get("/aed/nearby", response={200: dict, 400: NearestError})
def nearby_aeds(
    request,
    lat: float = Query(..., ge=-90, le=90, description="Your latitude, WGS84 (e.g. 52.2297)"),
    lon: float = Query(..., ge=-180, le=180, description="Your longitude, WGS84 (e.g. 21.0122)"),
    limit: int = Query(5, ge=1, le=20, description="How many AEDs, nearest first"),
    access: str | None = Query(None, description="Comma-separated: public, limited, private, unknown"),
    max_distance_m: float | None = Query(None, gt=0, le=100_000, description="Search radius in metres"),
    open_now: bool = OPEN_NOW,
    at: datetime | None = AT,
):
    """The nearest usable AEDs (same rules as /aed/nearest), each with its full public record, distance, availability
    and links. Backs the public "find the nearest AED" page. Not cached: every GPS fix is a different key, so a cache
    would hardly ever hit and would only keep visitors' positions in Redis. The KNN query on the GiST index is cheap."""
    wanted, error = _parse_access(access)
    if error:
        return 400, {"detail": error}
    base_url = _base_url(request)
    moment = at or timezone.now()
    return {
        "query": {"lat": lat, "lon": lon},
        "items": [
            {
                "distance_m": round(distance, 1),
                "aed": public_record(device),
                "availability": availability(device.opening_hours, moment),
                "links": links(device, lat, lon, base_url),
            }
            for device, distance in find_nearby(lat, lon, limit, wanted, max_distance_m, moment if open_now else None)
        ],
    }


@public.get("/aed/{device_id}", response={200: dict, 404: Detail, 410: Detail})
def aed_record(request, device_id: str, at: datetime | None = AT):
    """One AED as the reference record (the same fields as the exports), with its availability now and links. A
    device merged into another answers 301 to the one it was merged into; one no source lists any more answers 410.
    `AED-PL-DEMO` is the demo device with every field filled."""
    if device_id == DEMO_ID:
        device = DEMO_AED
    else:
        device = Device.objects.filter(pk=device_id).first()
        if device is None:
            return 404, {"detail": f"No AED {device_id}"}
        if device.merged_into_id:
            return HttpResponsePermanentRedirect(f"/api/aed/{device.merged_into_id}")
        if not device.active:
            return 410, {"detail": f"{device_id} is no longer listed by any source"}
    return {
        "demo": device.pk == DEMO_ID,
        "aed": public_record(device),
        "availability": availability(device.opening_hours, at),
        "links": links(device, None, None, _base_url(request)),
    }


@public.get("/changes")
def changes(
    request,
    since: datetime = SINCE,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Devices changed after `since`, oldest change first, for keeping a copy of the dataset in sync without
    downloading it all: `updated` (with the current record), `removed` (no source lists it any more) or `merged` (a
    duplicate, folded into `merged_into`). Start from a full export, then poll with the previous `as_of`."""
    since, as_of = _aware(since), timezone.now()
    qs = Device.objects.filter(updated_at__gt=since, updated_at__lte=as_of).order_by("updated_at", "id")
    items = []
    for device in qs[offset : offset + limit]:
        change = "merged" if device.merged_into_id else "updated" if device.active else "removed"
        items.append(
            {
                "id": device.pk,
                "change": change,
                "merged_into": device.merged_into_id,
                "updated_at": _iso(device.updated_at),
                "aed": public_record(device) if change == "updated" else None,
            }
        )
    return {"since": since.isoformat(), "as_of": as_of.isoformat(), "count": qs.count(), "items": items}


def event_dict(e: MaintenanceEvent) -> dict:
    return {
        "id": e.id,
        "kind": e.kind,
        "date": _iso(e.date),
        "details": e.details,
        "next_due": _iso(e.next_due),
        "source": e.source,
        "reported_by": e.reported_by,
        "created_at": _iso(e.created_at),
    }


@public.get("/devices/{device_id}")
def device_detail(request, device_id: str):
    device = get_object_or_404(Device, pk=device_id)
    body = list_item(device)
    for field in EXPORT_FIELDS + DETAIL_EXTRA:
        if field not in body and field != "sources":
            body[field] = _iso(getattr(device, field))
    body["municipality"] = boundaries.municipality(device.teryt)
    body["field_sources"] = device.field_sources
    body["records"] = [
        {
            "integration": r.integration.slug,
            "integration_name": r.integration.name,
            "source_record_id": r.source_record_id,
            "first_seen": _iso(r.first_seen),
            "last_seen": _iso(r.last_seen),
            "removed_at": _iso(r.removed_at),
            "is_valid": r.is_valid,
            "issues": r.issues,
            "data": r.data,
            "inferred": r.inferred,
        }
        for r in SourceRecord.objects.filter(device=device)
        .select_related("integration")
        .order_by("-integration__priority")
    ]
    body["events"] = [event_dict(e) for e in device.events.all()]
    return body


# dane.gov.pl checks a link with HEAD before downloading it (the harvester requires a 2xx on HEAD for its XML)
EXPORT_METHODS = ["GET", "HEAD"]


def _base_url(request) -> str:
    """Origin for absolute export links: an EXTRA_PUBLIC_BASE_URLS origin the request came through (the Host or any
    X-Forwarded-Host hop, since Next and nginx proxy /api), else PUBLIC_BASE_URL, else the request host."""
    if settings.EXTRA_PUBLIC_BASE_URLS:
        hosts = [h.strip() for h in request.headers.get("X-Forwarded-Host", "").split(",") if h.strip()]
        hosts.append(request.get_host())
        for host in hosts:
            for scheme in ("https", "http"):
                if f"{scheme}://{host}" in settings.EXTRA_PUBLIC_BASE_URLS:
                    return f"{scheme}://{host}"
    return settings.PUBLIC_BASE_URL or request.build_absolute_uri("/")


def export_response(request, fmt: str, filename: str):
    content, etag = get_export(fmt, _base_url(request))
    quoted = f'"{etag}"'
    if request.headers.get("If-None-Match") == quoted:
        return HttpResponseNotModified()
    response = HttpResponse(content, content_type=CONTENT_TYPES[fmt])
    response["ETag"] = quoted
    response["Cache-Control"] = "public, max-age=60"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    if fmt == "jsonld":  # JSON-LD 1.1 §6.1: the context is also announced in an HTTP Link header
        response["Link"] = '<https://schema.org/>; rel="http://www.w3.org/ns/json-ld#context"'
    if fmt == "csv":  # CSVW §5.2 (Model for Tabular Data): where the table description lives
        metadata = f"{_base_url(request).rstrip('/')}/api/export/aeds.csv-metadata.json"
        response["Link"] = f'<{metadata}>; rel="describedby"; type="application/csvm+json"'
    return response


@public.api_operation(EXPORT_METHODS, "/export/aeds.csv-metadata.json")
def export_csv_metadata(request):
    """CSVW metadata (W3C Model for Tabular Data) of aeds.csv: column titles, descriptions and datatypes, the special
    sign "." as null, and a URL per record, so the CSV converts to JSON-LD/RDF (Standard techniczny §4.3, 4★)."""
    from .reference_scope import build_csvw_json

    content = build_csvw_json(_base_url(request))
    etag = f'"{hashlib.md5(content).hexdigest()}"'  # noqa: S324 — an ETag, not security
    if request.headers.get("If-None-Match") == etag:
        return HttpResponseNotModified()
    response = HttpResponse(content, content_type="application/csvm+json")
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=60"
    return response


@public.api_operation(EXPORT_METHODS, "/export/archiwum")
def export_versions(request):
    """Every stored daily version of the data files, newest first, with their addresses (they never change)."""
    from .exports import ARCHIVE_PATH, ARCHIVED, archive_versions

    base = _base_url(request).rstrip("/")
    return {
        "versions": [
            {"data_date": day, "files": {name: f"{base}{ARCHIVE_PATH}/{day}/{name}" for name in ARCHIVED.values()}}
            for day in archive_versions()
        ]
    }


@public.api_operation(EXPORT_METHODS, "/export/archiwum/{day}/{name}")
def export_version_file(request, day: str, name: str):
    """One file of one daily version, as it was published that day."""
    from django.http import FileResponse, Http404

    from .exports import ARCHIVED, archived_path

    path = archived_path(day, name)
    if path is None:
        raise Http404
    fmt = next(f for f, n in ARCHIVED.items() if n == name)
    stat = path.stat()
    etag = f'"{day}-{stat.st_size}-{int(stat.st_mtime)}"'
    if request.headers.get("If-None-Match") == etag:
        return HttpResponseNotModified()
    stem, dot, extension = name.partition(".")
    response = FileResponse(
        path.open("rb"),
        content_type=CONTENT_TYPES[fmt],
        as_attachment=True,
        filename=f"aed-polska-{stem.removeprefix('aeds').strip('-') or 'dane'}-{day}{dot}{extension}",
    )
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=86400"
    if fmt == "csv":
        metadata = f"{_base_url(request).rstrip('/')}/api/export/aeds.csv-metadata.json"
        response["Link"] = f'<{metadata}>; rel="describedby"; type="application/csvm+json"'
    return response


@public.api_operation(EXPORT_METHODS, "/export/aeds-sources.csv")
def export_sources_csv(request):
    """Which source records each AED merges, one (aed_id, source) pair per row: the CSV's list column, normalised."""
    return export_response(request, "sources_csv", "aed-polska-zrodla.csv")


@public.api_operation(EXPORT_METHODS, "/export/aeds.geojson")
def export_geojson(request):
    return export_response(request, "geojson", "aed-polska.geojson")


@public.api_operation(EXPORT_METHODS, "/export/aeds.csv")
def export_csv(request):
    return export_response(request, "csv", "aed-polska.csv")


@public.api_operation(EXPORT_METHODS, "/export/aeds.json")
def export_json(request):
    return export_response(request, "json", "aed-polska.json")


@public.api_operation(EXPORT_METHODS, "/export/aeds.jsonld")
def export_jsonld(request):
    return export_response(request, "jsonld", "aed-polska.jsonld")


@public.api_operation(EXPORT_METHODS, "/export/schema.xlsx")
def export_schema(request):
    return export_response(request, "xlsx", "wzorcowy-zakres-danych-aed.xlsx")


@public.api_operation(EXPORT_METHODS, "/export/schema-template.csv")
def export_schema_template_csv(request):
    """The first sheet of schema.xlsx (Polish headers, example rows) as CSV, as the ministry ships reference scopes."""
    return export_response(request, "template_csv", "wzorcowy-zakres-danych-aed.csv")


@public.api_operation(EXPORT_METHODS, "/export/schema-template.xlsx")
def export_schema_template_xlsx(request):
    """The template alone as a single-sheet XLSX for dane.gov.pl: one header row and the example rows as an Excel
    table, no merged cells, formulas or notes (Standard techniczny §3.1)."""
    return export_response(request, "template_xlsx", "wzorcowy-zakres-danych-aed-szablon.xlsx")


@public.api_operation(EXPORT_METHODS, "/export/wykaz-chronionych-danych.xlsx")
def export_protected_data_list(request):
    """Our list of protected data (DGA), the file dane.gov.pl copies into its nationwide table every night."""
    return export_response(request, "dga_xlsx", "misja-aed-wykaz-chronionych-danych.xlsx")


@public.api_operation(EXPORT_METHODS, "/export/schema.txt")
def export_schema_txt(request):
    return export_response(request, "txt", "slownik-pol-aed.txt")


@public.api_operation(EXPORT_METHODS, "/export/notes.txt")
def export_notes_txt(request):
    """Licence and every departure from a dane.gov.pl recommendation, with the reason (a TXT supplement)."""
    return export_response(request, "notes", "informacje-o-zbiorze-aed.txt")


@public.api_operation(EXPORT_METHODS, "/export/dataset.json")
def export_dataset(request):
    """dane.gov.pl-shaped metadata: the dataset, its resources (each with an absolute link to register on the portal),
    the field dictionary as a supplement, and the sources behind the merge."""
    return get_dataset(_base_url(request))


@public.api_operation(EXPORT_METHODS, "/export/harvester.xml")
def export_harvester_xml(request):
    """The dataset in the dane.gov.pl harvester XML schema: register this URL once as a data source (type XML) and the
    portal keeps metadata and resources in sync. Served inline (not as an attachment) with an XML Content-Type."""
    content, md5 = get_harvester_xml(_base_url(request))
    response = HttpResponse(content, content_type=CONTENT_TYPES["xml"])
    response["ETag"] = f'"{md5}"'
    response["Cache-Control"] = "public, max-age=60"
    return response


@public.api_operation(EXPORT_METHODS, "/export/harvester.md5")
def export_harvester_md5(request):
    """MD5 of harvester.xml; the portal fetches it from the same URL with .md5 and rejects a mismatch."""
    _, md5 = get_harvester_xml(_base_url(request))
    return HttpResponse(f"{md5}\n", content_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------- admin


class EventIn(Schema):
    kind: MaintenanceEvent.Kind
    date: date
    details: str = ""
    next_due: date | None = None


@admin.post("/devices/{device_id}/events")
def add_event(request, device_id: str, payload: EventIn):
    device = get_object_or_404(Device, pk=device_id)
    event, _ = MaintenanceEvent.objects.update_or_create(
        device=device,
        kind=payload.kind,
        date=payload.date,
        source="manual",
        defaults={"details": payload.details, "next_due": payload.next_due, "reported_by": request.user.username},
    )
    recompute([device.pk])
    bump_data_version()
    return event_dict(event)


def match_dict(m: MatchCandidate) -> dict:
    return {
        "id": m.id,
        "distance_m": round(m.distance_m, 1),
        "status": m.status,
        "reason": m.reason,
        "created_at": _iso(m.created_at),
        "device_a": list_item(m.device_a),
        "device_b": list_item(m.device_b),
    }


@admin.get("/matches")
def matches(request, status: str = "pending", limit: int = 50, offset: int = 0):
    qs = (
        MatchCandidate.objects.filter(status=status).select_related("device_a", "device_b").order_by("distance_m", "id")
    )
    return {"count": qs.count(), "items": [match_dict(m) for m in qs[offset : offset + min(limit, 200)]]}


@admin.post("/matches/{match_id}/accept")
def accept(request, match_id: int):
    match = get_object_or_404(
        MatchCandidate.objects.select_related("device_a", "device_b"), pk=match_id, status="pending"
    )
    accept_match(match)
    bump_data_version()
    return match_dict(match)


@admin.post("/matches/{match_id}/reject")
def reject(request, match_id: int):
    match = get_object_or_404(
        MatchCandidate.objects.select_related("device_a", "device_b"), pk=match_id, status="pending"
    )
    match.status, match.decided_at = MatchCandidate.Status.REJECTED, timezone.now()
    match.save(update_fields=["status", "decided_at"])
    bump_data_version()
    return match_dict(match)
