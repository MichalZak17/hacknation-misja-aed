"""The nearest usable AED to a point: the rescuer's question (where is it, can I get to it, does it work) as one call.

`GET /api/aed/nearest` skips devices a rescuer cannot count on being there: AEDs carried in vehicles (their
coordinates are only where the vehicle is stationed) and devices reported out of service, missing or decommissioned.
`demo=true` answers with DEMO_AED, a made-up device with every field of the reference record filled, so API clients can
see the full response shape; it is never stored and never exported.
"""

import math
from datetime import date, datetime

from django.db import connection

from . import boundaries
from .availability import availability, is_open
from .models import Device
from .schema import ADDRESS_PART_FIELDS, BOOL_FIELDS, DATE_FIELDS, DATETIME_FIELDS, EXPORT_FIELDS, SCHEMA

UNUSABLE_STATUSES = ("out_of_service", "missing", "decommissioned")
DEMO_ID = "AED-PL-DEMO"
OPEN_BATCH = 200  # `open_now`: candidates read per query
OPEN_SCAN_LIMIT = 4000  # `open_now`: nearest candidates checked at most


def _iso(value):
    return value.isoformat() if isinstance(value, date | datetime) else value


def public_record(device: Device) -> dict:
    """Every field of the reference record (the same as the exports), plus the municipality name and last update."""
    body = {field: _iso(getattr(device, field)) for field in EXPORT_FIELDS}
    body["municipality"] = boundaries.municipality(device.teryt) if device.pk != DEMO_ID else "Warszawa"
    body["updated_at"] = _iso(device.updated_at)
    return body


def _demo_device() -> Device:
    values = {}
    for f in SCHEMA:
        if f.field in ADDRESS_PART_FIELDS:
            continue  # derived from `address` on read
        if f.field in DATE_FIELDS:
            value = date.fromisoformat(f.example)
        elif f.field in DATETIME_FIELDS:
            value = datetime.fromisoformat(f.example)
        elif f.field in BOOL_FIELDS:
            value = f.example == "true"
        elif f.field in {"access_conditions", "sources"}:
            value = f.example.split(";")
        elif f.field in {"lat", "lon", "coordinate_accuracy_m"}:
            value = float(f.example)
        else:
            value = f.example
        values[f.field] = value
    values["id"] = DEMO_ID
    values["placement"] = "inside_building"  # the schema example's building, floor and indoor describe a metro station
    device = Device(**values)
    device.updated_at = datetime.fromisoformat("2026-11-20T03:15:00+01:00")
    return device


DEMO_AED = _demo_device()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_nearby(
    lat: float,
    lon: float,
    limit: int = 1,
    access: list[str] | None = None,
    max_distance_m: float | None = None,
    open_at: datetime | None = None,
) -> list[tuple[Device, float]]:
    """(device, distance in metres) of the closest usable active AEDs, nearest first. Uses the GiST index on `geom`
    (KNN). With `open_at`, only AEDs whose opening hours cover that moment: candidates are read nearest first in
    batches and checked in Python, up to OPEN_SCAN_LIMIT of them."""
    where = [
        "active",
        "NOT is_mobile",
        "placement <> 'vehicle'",
        "NOT operational_status = ANY(%(unusable)s)",
    ]
    params = {"lat": lat, "lon": lon, "unusable": list(UNUSABLE_STATUSES)}
    if access:
        where.append("access = ANY(%(access)s)")
        params["access"] = list(access)
    if max_distance_m is not None:
        where.append("ST_DWithin(geom, (SELECT p FROM here), %(max)s)")
        params["max"] = max_distance_m
    if open_at is not None:
        where.append("opening_hours IS NOT NULL AND opening_hours <> ''")
    sql = f"""
        WITH here AS (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography AS p)
        SELECT id, ST_Distance(geom, (SELECT p FROM here)), opening_hours
        FROM devices_device
        WHERE {" AND ".join(where)}
        ORDER BY geom <-> (SELECT p FROM here), id
        LIMIT %(limit)s OFFSET %(offset)s
    """
    batch = limit if open_at is None else max(OPEN_BATCH, limit * 10)
    rows: list[tuple[str, float]] = []
    with connection.cursor() as cursor:
        for offset in range(0, OPEN_SCAN_LIMIT if open_at else batch, batch):
            cursor.execute(sql, params | {"limit": batch, "offset": offset})
            fetched = cursor.fetchall()
            rows += [(id_, d) for id_, d, hours in fetched if open_at is None or is_open(hours, open_at)]
            if len(rows) >= limit or len(fetched) < batch:
                break
    rows = rows[:limit]
    found = Device.objects.in_bulk([row[0] for row in rows])
    return [(found[id_], distance) for id_, distance in rows if id_ in found]


def find_nearest(
    lat: float,
    lon: float,
    access: list[str] | None = None,
    max_distance_m: float | None = None,
    open_at: datetime | None = None,
):
    """(device, distance in metres) of the closest usable active AED, or None."""
    found = find_nearby(lat, lon, 1, access, max_distance_m, open_at)
    return found[0] if found else None


def links(device: Device, lat: float | None, lon: float | None, base_url: str) -> dict:
    """`self` (provenance detail), `record` (the reference record), an OSM map and Google walking directions — from
    the query point, or from wherever the user is when there is none."""
    base = base_url.rstrip("/")
    to = f"{device.lat},{device.lon}"
    origin = f"&origin={lat},{lon}" if lat is not None and lon is not None else ""
    return {
        "self": None if device.pk == DEMO_ID else f"{base}/api/devices/{device.pk}",
        "record": f"{base}/api/aed/{device.pk}",
        "map": f"https://www.openstreetmap.org/?mlat={device.lat}&mlon={device.lon}#map=19/{device.lat}/{device.lon}",
        "directions": f"https://www.google.com/maps/dir/?api=1{origin}&destination={to}&travelmode=walking",
    }


def nearest_response(
    device: Device, distance_m: float, lat: float, lon: float, base_url: str, at: datetime | None = None
) -> dict:
    return {
        "demo": device.pk == DEMO_ID,
        "query": {"lat": lat, "lon": lon},
        "distance_m": round(distance_m, 1),
        "aed": public_record(device),
        "availability": availability(device.opening_hours, at),
        "links": links(device, lat, lon, base_url),
    }
