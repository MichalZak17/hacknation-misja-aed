"""Reports from the public form (/zglos): anyone can tell us about a missing AED, a wrong position or detail, a device
that does not work or is locked, or offer data as its owner. Admins read and resolve them in the panel inbox.

Reports never reach the dataset by themselves: nothing here touches Device fields, exports or the merge. An admin who
confirms a report fixes the data through a source (operator file, maintenance event) with its own provenance.

Spam protection, without accounts or captchas: a honeypot field that people never see (a filled one gets a normal
answer and is dropped), payload limits, and a fixed-window rate limit per sender in the Django cache (Redis), plus a
global ceiling. The sender's IP is kept only as a salted hash, for that limit.
"""

import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.security import django_auth

from integrations.engine import POLAND, in_box

from .models import Device, DeviceReport

router = Router(tags=["reports"])

DESCRIPTION_MAX = 2000
RATE_WINDOW_S = 3600
RATE_PER_SENDER = 5  # reports per sender per hour
RATE_GLOBAL = 200  # reports per hour from everyone, a ceiling if a sender rotates addresses


class ReportIn(Schema):
    kind: str
    device_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str = ""
    contact_email: str | None = None
    # Honeypot: hidden from people in the form, bots fill every field
    website: str | None = None


class ReportUpdate(Schema):
    status: DeviceReport.Status | None = None
    admin_note: str | None = None


def client_ip(request) -> str:
    """The first X-Forwarded-For hop (the edge proxy replaces whatever the client sent), else the socket address."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    first = forwarded.split(",")[0].strip()
    return first or request.META.get("REMOTE_ADDR", "")


def ip_hash(ip: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"report-ip:{ip}".encode(), hashlib.sha256).hexdigest()


def _hit(key: str, limit: int) -> bool:
    """Count one request in a fixed window; True when the limit is already used up."""
    cache.add(key, 0, RATE_WINDOW_S)
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, RATE_WINDOW_S)
        count = 1
    return count > limit


def rate_limited(sender: str) -> bool:
    return _hit(f"reports:rate:{sender}", RATE_PER_SENDER) or _hit("reports:rate:all", RATE_GLOBAL)


def validate(payload: ReportIn) -> tuple[dict, dict]:
    """Clean values for the model, and Polish messages per field for the form."""
    errors: dict[str, str] = {}
    clean: dict = {}

    if payload.kind not in DeviceReport.Kind.values:
        errors["kind"] = "Wybierz, czego dotyczy zgłoszenie."
    clean["kind"] = payload.kind

    description = (payload.description or "").strip()
    if not description:
        errors["description"] = "Opisz krótko, co się nie zgadza."
    elif len(description) > DESCRIPTION_MAX:
        errors["description"] = f"Opis może mieć najwyżej {DESCRIPTION_MAX} znaków."
    clean["description"] = description

    email = (payload.contact_email or "").strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors["contact_email"] = "Wpisz adres e-mail w postaci nazwa@domena.pl albo zostaw pole puste."
    clean["contact_email"] = email

    if (payload.lat is None) != (payload.lon is None):
        errors["location"] = "Podaj obie współrzędne albo żadnej."
    elif payload.lat is not None and not in_box(payload.lat, payload.lon, POLAND):
        errors["location"] = "To miejsce leży poza Polską. Sprawdź współrzędne (szerokość 49–55, długość 14–24)."
    else:
        clean["lat"] = round(payload.lat, 6) if payload.lat is not None else None
        clean["lon"] = round(payload.lon, 6) if payload.lon is not None else None

    device_id = (payload.device_id or "").strip().upper()
    clean["device"] = None
    if device_id:
        device = Device.objects.select_related("merged_into").filter(pk=device_id).first()
        if device is None:
            errors["device_id"] = f"Nie znamy AED o numerze {device_id[:40]}. Sprawdź numer albo zostaw pole puste."
        else:
            clean["device"] = device.merged_into or device  # a merged duplicate points at the device that stayed

    return clean, errors


def report_dict(r: DeviceReport) -> dict:
    d = r.device
    return {
        "id": r.id,
        "kind": r.kind,
        "kind_label": r.get_kind_display(),
        "status": r.status,
        "device": (
            {"id": d.id, "name": d.building_name, "address": d.address, "city": d.city, "lat": d.lat, "lon": d.lon}
            if d
            else None
        ),
        "lat": r.lat,
        "lon": r.lon,
        "description": r.description,
        "contact_email": r.contact_email,
        "admin_note": r.admin_note,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


# ---------------------------------------------------------------- public


@router.post("/reports", response={201: dict, 400: dict, 429: dict})
def create_report(request, payload: ReportIn):
    """Public, no login. Never published: the report waits for an admin in the panel."""
    if payload.website:
        return 201, {"received": True}  # honeypot: look successful, store nothing
    sender = ip_hash(client_ip(request))
    if rate_limited(sender):
        return 429, {"detail": "Wysłano już kilka zgłoszeń z tego adresu. Spróbuj ponownie za godzinę."}
    clean, errors = validate(payload)
    if errors:
        return 400, {"detail": "Popraw zaznaczone pola.", "errors": errors}
    DeviceReport.objects.create(**clean, ip_hash=sender)
    return 201, {"received": True}


# ---------------------------------------------------------------- admin


@router.get("/reports", auth=django_auth)
def list_reports(request, status: str | None = None, limit: int = 50, offset: int = 0):
    qs = DeviceReport.objects.select_related("device")
    counts = dict.fromkeys(DeviceReport.Status.values, 0) | {
        row["status"]: row["n"] for row in qs.values("status").annotate(n=Count("id")).order_by()
    }
    if status:
        qs = qs.filter(status=status)
    limit = max(1, min(limit, 200))
    return {"count": qs.count(), "counts": counts, "items": [report_dict(r) for r in qs[offset : offset + limit]]}


@router.patch("/reports/{report_id}", auth=django_auth)
def update_report(request, report_id: int, payload: ReportUpdate):
    report = get_object_or_404(DeviceReport.objects.select_related("device"), pk=report_id)
    if payload.status is not None:
        report.status = payload.status
    if payload.admin_note is not None:
        report.admin_note = payload.admin_note.strip()[:DESCRIPTION_MAX]
    report.save(update_fields=["status", "admin_note", "updated_at"])
    return report_dict(report)


@router.delete("/reports/{report_id}", response={204: None}, auth=django_auth)
def delete_report(request, report_id: int):
    get_object_or_404(DeviceReport, pk=report_id).delete()
    return 204, None
