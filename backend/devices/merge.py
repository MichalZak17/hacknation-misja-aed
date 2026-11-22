"""Merging source records into devices.

1. A valid, live record already linked to a device just refreshes that device.
2. An unlinked record joins a device through stable IDs: its own `refs` to another source's record, or another
   source's record that refers to it (OSM `ref:api-um-warszawa-pl` ↔ Warsaw `defib_id`).
3. Otherwise it becomes a new device. Devices of different sources within MATCH_DISTANCE_M become a MatchCandidate
   for review — nearby AEDs can be on different floors or entrances, so distance alone never merges.
4. Every touched device is recomputed: per field, the highest-priority source that states it wins, except dates of
   replacements and checks, where the most recent wins; manual and operator maintenance events overlay those dates.
   A field no source states may be filled from what the LLM read in the records' free text (`SourceRecord.inferred`,
   integrations/enrichment), highest-priority record first; `field_sources` then says `"method": "inferred"`.
5. A device whose sources state no `teryt` or `city` gets them from its coordinates and the official boundaries
   (devices/boundaries.py) when they are certain: the municipality always, the town only inside a town, nothing within
   a few metres of a boundary. `field_sources` says `"source": "prg", "method": "geocoded"`. Street, house number and
   postal code are never derived from coordinates.
"""

import json
from collections import defaultdict
from datetime import date, datetime

from django.conf import settings
from django.db import connection
from django.utils import timezone

from integrations.connectors.common import to_floor
from integrations.enrichment import MERGEABLE as INFERABLE_FIELDS
from integrations.models import SourceRecord

from . import boundaries
from .models import Device, MaintenanceEvent, MatchCandidate
from .readiness import compute_readiness
from .schema import DATE_FIELDS, DATETIME_FIELDS, ENUM_FIELDS, LATEST_DATE_FIELDS, LIST_FIELDS, MERGE_FIELDS

# Maintenance event kind → (date field, next-due field) on Device
EVENT_FIELDS = {
    "pads_replaced": ("pads_replaced_on", "pads_expiry_date"),
    "battery_replaced": ("battery_installed_on", "battery_expiry_date"),
    "inspection": ("last_inspection_on", "next_inspection_due"),
    "used_in_rescue": ("last_used_on", None),
}
DEVICE_UPDATE_FIELDS = MERGE_FIELDS + ["lat", "lon", "readiness", "active", "source_count", "sources", "field_sources"]


def new_device_ids(count: int) -> list[str]:
    if not count:
        return []
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('device_id_seq') FROM generate_series(1, %s)", [count])
        return [f"AED-PL-{n:06d}" for (n,) in cursor.fetchall()]


def _parse(field: str, value):
    if value is None:
        return None
    if field in DATE_FIELDS:
        return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    if field in DATETIME_FIELDS:
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if field == "floor":  # records stored before floors were normalised may still hold "0.5"
        return to_floor(value)
    return value


def merge_records(record_ids: list[int]) -> dict:
    records = list(SourceRecord.objects.filter(pk__in=record_ids).select_related("integration"))
    affected: set[str] = set()
    stats = {"linked_by_id": 0, "new_devices": 0, "unlinked": 0, "candidates": 0}

    # Records that are invalid or gone leave their device (which may become inactive)
    for record in records:
        if record.device_id and (not record.is_valid or record.removed_at):
            affected.add(record.device_id)
            if not record.is_valid:
                record.device_id = None
                stats["unlinked"] += 1
    SourceRecord.objects.bulk_update([r for r in records if not r.is_valid], ["device"], batch_size=1000)

    live = [r for r in records if r.is_valid and r.removed_at is None]
    for record in live:
        if record.device_id:
            affected.add(record.device_id)

    # Stable-ID links, both directions
    unlinked = [r for r in live if not r.device_id]
    if unlinked:
        referring = defaultdict(list)  # (slug, id) the record points at → records pointing at it
        for other in SourceRecord.objects.filter(
            data__has_key="refs", removed_at__isnull=True, is_valid=True
        ).select_related("integration"):
            for slug, ref_id in (other.data.get("refs") or {}).items():
                referring[(slug, str(ref_id))].append(other)
        targets = {}
        wanted = {(slug, str(ref_id)) for r in unlinked for slug, ref_id in (r.data.get("refs") or {}).items()}
        if wanted:
            for target in SourceRecord.objects.filter(
                integration__slug__in={s for s, _ in wanted},
                source_record_id__in={i for _, i in wanted},
                device__isnull=False,
            ).select_related("integration"):
                targets[(target.integration.slug, target.source_record_id)] = target.device_id
        for record in unlinked:
            device_id = None
            for slug, ref_id in (record.data.get("refs") or {}).items():
                device_id = device_id or targets.get((slug, str(ref_id)))
            if not device_id:
                for other in referring.get((record.integration.slug, record.source_record_id), []):
                    if other.device_id:
                        device_id = other.device_id
                        break
            if device_id:
                record.device_id = device_id
                affected.add(device_id)
                stats["linked_by_id"] += 1

    still = [r for r in unlinked if not r.device_id]
    ids = new_device_ids(len(still))
    devices = [Device(id=device_id, lat=r.lat, lon=r.lon) for device_id, r in zip(ids, still, strict=True)]
    Device.objects.bulk_create(devices, batch_size=1000)
    for device_id, record in zip(ids, still, strict=True):
        record.device_id = device_id
        affected.add(device_id)
    stats["new_devices"] = len(ids)
    SourceRecord.objects.bulk_update(unlinked, ["device"], batch_size=1000)

    recompute(list(affected))
    stats["candidates"] = propose_matches(ids)
    return stats


def recompute(device_ids: list[str]) -> None:
    """Rebuild each device's fields from its live records and maintenance events."""
    for start in range(0, len(device_ids), 2000):
        chunk = device_ids[start : start + 2000]
        records = defaultdict(list)
        for record in SourceRecord.objects.filter(device_id__in=chunk).select_related("integration"):
            records[record.device_id].append(record)
        events = defaultdict(list)
        for event in MaintenanceEvent.objects.filter(device_id__in=chunk):
            events[event.device_id].append(event)
        devices = list(Device.objects.filter(pk__in=chunk))
        new_events = []
        for device in devices:
            new_events += apply(device, records[device.pk], events[device.pk])
        geocode(devices)
        fast_update(devices)
        MaintenanceEvent.objects.bulk_create(new_events, ignore_conflicts=True, batch_size=1000)


def geocode(devices: list[Device]) -> None:
    """Fill `teryt` and `city` no source states from the boundaries the coordinates fall in (step 5 above)."""
    fields = ("teryt", "city")
    wanted = [d for d in devices if d.active and any(getattr(d, f) is None for f in fields)]
    found = boundaries.lookup([(d.pk, d.lat, d.lon) for d in wanted])
    today = timezone.localdate().isoformat()
    for device in wanted:
        hit = found.get(device.pk)
        for field in fields:
            if hit and hit[field] and getattr(device, field) is None:
                setattr(device, field, hit[field])
                device.field_sources[field] = {
                    "source": boundaries.SOURCE,
                    "seen": hit["version"] or today,
                    "method": "geocoded",
                }


def fast_update(devices: list[Device]) -> None:
    """One UPDATE per 2000 devices from a JSON array (jsonb_populate_recordset). Django's bulk_update builds a CASE per
    row and field — about 7 ms per device with ~45 fields, minutes for a national load."""
    columns = ", ".join(DEVICE_UPDATE_FIELDS)
    values = ", ".join(f"r.{c}" for c in DEVICE_UPDATE_FIELDS)
    sql = (
        f"UPDATE devices_device d SET ({columns}) = ({values}), updated_at = now() "
        "FROM jsonb_populate_recordset(NULL::devices_device, %s::jsonb) r WHERE d.id = r.id"
    )

    def plain(value):
        return value.isoformat() if isinstance(value, date | datetime) else value

    with connection.cursor() as cursor:
        for start in range(0, len(devices), 2000):
            rows = [
                {"id": d.pk} | {f: plain(getattr(d, f)) for f in DEVICE_UPDATE_FIELDS}
                for d in devices[start : start + 2000]
            ]
            cursor.execute(sql, [json.dumps(rows, ensure_ascii=False)])


def apply(device: Device, records: list, events: list) -> list[MaintenanceEvent]:
    live = [r for r in records if r.is_valid and r.removed_at is None]
    live.sort(key=lambda r: (-r.integration.priority, -r.last_seen.timestamp()))
    device.active = bool(live) and device.merged_into_id is None
    device.source_count = len({r.integration.slug for r in live})
    device.sources = sorted({r.integration.slug for r in live})
    if not live:
        device.readiness = compute_readiness(device)
        return []

    device.lat, device.lon = live[0].lat, live[0].lon
    field_sources = {"lat": {"source": live[0].integration.slug, "seen": live[0].last_seen.date().isoformat()}}
    for field in MERGE_FIELDS:
        chosen, chosen_record = None, None
        for record in live:
            value = record.data.get(field)
            if value is None or (field in ENUM_FIELDS and value == "unknown") or (field in LIST_FIELDS and not value):
                continue
            value = _parse(field, value)
            if value is None:
                continue
            if field in LATEST_DATE_FIELDS:
                if chosen is None or value > chosen:
                    chosen, chosen_record = value, record
            else:
                chosen, chosen_record = value, record
                break
        inferred = False
        if chosen is None and field in INFERABLE_FIELDS:
            for record in live:
                value = (record.inferred or {}).get(field)
                if value is not None:
                    chosen, chosen_record, inferred = value, record, True
                    break
        if chosen is None and field in ENUM_FIELDS:
            chosen = "unknown"
        if field == "is_mobile" and chosen is None:
            chosen = False
        setattr(device, field, chosen)
        if chosen_record is not None:
            field_sources[field] = {
                "source": chosen_record.integration.slug,
                "seen": chosen_record.last_seen.date().isoformat(),
            }
            if inferred:
                field_sources[field]["method"] = "inferred"

    # Maintenance history: source-stated dates become events; every event (manual included) overlays the dates
    new_events = []
    for kind, (date_field, due_field) in EVENT_FIELDS.items():
        value = getattr(device, date_field)
        if value and date_field in field_sources:
            new_events.append(
                MaintenanceEvent(
                    device=device,
                    kind=kind,
                    date=value,
                    source=field_sources[date_field]["source"],
                    next_due=getattr(device, due_field) if due_field else None,
                    details="Z danych źródła",
                )
            )
    for event in sorted(events, key=lambda e: e.date):
        if event.kind == "decommissioned":
            device.operational_status = "decommissioned"
            field_sources["operational_status"] = {"source": event.source, "seen": event.date.isoformat()}
            continue
        if event.kind == "self_test":
            moment = timezone.make_aware(datetime.combine(event.date, datetime.min.time()))
            if not device.last_self_test_at or moment > device.last_self_test_at:
                device.last_self_test_at = moment
                device.last_self_test_result = event.details or device.last_self_test_result
            continue
        if event.kind not in EVENT_FIELDS:
            continue
        date_field, due_field = EVENT_FIELDS[event.kind]
        current = getattr(device, date_field)
        if current is None or event.date >= current:
            setattr(device, date_field, event.date)
            field_sources[date_field] = {"source": event.source, "seen": event.date.isoformat()}
            if due_field and event.next_due:
                setattr(device, due_field, event.next_due)
                field_sources[due_field] = {"source": event.source, "seen": event.date.isoformat()}
    device.field_sources = field_sources
    device.readiness = compute_readiness(device)
    return new_events


def propose_matches(device_ids: list[str]) -> int:
    """Candidates between the given devices and active devices that share no source with them."""
    if not device_ids:
        return 0
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO devices_matchcandidate (device_a_id, device_b_id, distance_m, reason, status, created_at)
            SELECT DISTINCT LEAST(a.id, b.id), GREATEST(a.id, b.id), ST_Distance(a.geom, b.geom),
                   'Odległość ≤ ' || %(distance)s::int || ' m, różne źródła', 'pending', now()
            FROM devices_device a
            JOIN devices_device b ON b.id <> a.id AND ST_DWithin(a.geom, b.geom, %(distance)s)
            WHERE a.id = ANY(%(ids)s) AND a.active AND b.active
              AND NOT (a.sources ?| ARRAY(SELECT jsonb_array_elements_text(b.sources)))
            ON CONFLICT (device_a_id, device_b_id) DO NOTHING
            """,
            {"ids": device_ids, "distance": settings.MATCH_DISTANCE_M},
        )
        return cursor.rowcount


def accept_match(match: MatchCandidate) -> MatchCandidate:
    """Merge device_b into device_a: records and events move, device_b stays as an inactive pointer."""
    keep, gone = match.device_a, match.device_b
    SourceRecord.objects.filter(device=gone).update(device=keep)
    for event in MaintenanceEvent.objects.filter(device=gone):
        if not MaintenanceEvent.objects.filter(
            device=keep, kind=event.kind, date=event.date, source=event.source
        ).exists():
            event.device = keep
            event.save(update_fields=["device"])
    gone.merged_into = keep
    gone.active = False
    gone.save(update_fields=["merged_into", "active", "updated_at"])  # the changes feed reports the merge
    recompute([keep.pk, gone.pk])
    match.status, match.decided_at = MatchCandidate.Status.ACCEPTED, timezone.now()
    match.save(update_fields=["status", "decided_at"])
    MatchCandidate.objects.filter(status="pending").filter(device_a=gone).delete()
    MatchCandidate.objects.filter(status="pending").filter(device_b=gone).delete()
    return match
