"""Which municipality and town a point lies in, from the official boundary register PRG (GUGiK).

Most OSM AEDs carry no address: the point sits inside a building, and the building's name and address live on another
OSM object that OpenAEDMap does not send. The coordinates still tell us, with certainty, the municipality (TERYT) and,
in a town, the town. This module answers that and nothing more; street, house number and postal code are never derived
from coordinates, because no official dataset maps an area to them reliably (Polish postal codes belong to streets and
number ranges, and the nearest address point is often the wrong building).

Data: layer A05 "jednostki ewidencyjne" (cadastral units) of the PRG package, ~3,200 polygons in ETRS89. Each unit's
code ends in its kind, which says whether the unit is a town:

    _1  urban municipality (gmina miejska)          → teryt XXXXXX1, city = the town
    _2  rural municipality (gmina wiejska)          → teryt XXXXXX2, no city
    _4  town of an urban-rural municipality         → teryt XXXXXX3, city = the town
    _5  rural area of an urban-rural municipality   → teryt XXXXXX3, no city
    _8  district of Warsaw (dzielnica)              → teryt 1465011, city Warszawa
    _9  district of Kraków/Łódź/Poznań/Wrocław      → that city's teryt and name

A rural area has many villages and no official village boundaries, so it gives no city. Near a boundary the answer can
be wrong (OSM coordinates are a few metres off, and so is a boundary drawn on a map), so a value is used only when every
unit within BORDER_MARGIN_M agrees on it.

`load_boundaries` (management command) fills the AdminUnit table; the merge (devices/merge.py) calls `lookup` for
devices whose sources state no `teryt` or `city`, and marks what it fills with `"method": "geocoded"`.
"""

import json
import logging
import zipfile
from datetime import date
from pathlib import Path

import httpx
from django.conf import settings
from django.db import connection, transaction

logger = logging.getLogger(__name__)

PRG_URL = "https://opendata.geoportal.gov.pl/prg/granice/00_jednostki_administracyjne.zip"
LAYER = "A05_Granice_jednostek_ewidencyjnych"
SOURCE = "prg"  # `source` in a device's field_sources for values filled here
BORDER_MARGIN_M = 30
# Districts (_9) of the cities split into delegatury, by powiat code
DISTRICT_CITIES = {"0264": "Wrocław", "1061": "Łódź", "1261": "Kraków", "3064": "Poznań"}
SUFFIXES = (" - gmina miejska", " - gmina wiejska", " - miasto", " - obszar wiejski")


def unit_values(code: str, name: str) -> dict:
    """PRG cadastral unit → the municipality's TERYT code, the town (or None) and a display name for the municipality.

    '121508_2', 'Zawoja - gmina wiejska' → {'teryt': '1215082', 'city': None, 'municipality': 'gmina wiejska Zawoja'}
    """
    number, kind = code.split("_")
    base = name
    for suffix in SUFFIXES:
        base = base.removesuffix(suffix)
    if kind == "1":
        return {"teryt": f"{number}1", "city": base, "municipality": f"gmina miejska {base}"}
    if kind == "2":
        return {"teryt": f"{number}2", "city": None, "municipality": f"gmina wiejska {base}"}
    if kind in ("4", "5"):
        return {
            "teryt": f"{number}3",
            "city": base if kind == "4" else None,
            "municipality": f"gmina miejsko-wiejska {base}",
        }
    if kind == "8":
        return {"teryt": "1465011", "city": "Warszawa", "municipality": "gmina miejska Warszawa"}
    if kind == "9":
        city = DISTRICT_CITIES[number[:4]]
        return {"teryt": f"{number[:4]}011", "city": city, "municipality": f"gmina miejska {city}"}
    raise ValueError(f"Unknown PRG unit kind: {code} {name}")


class RemoteFile:
    """A seekable read-only view of a URL through HTTP range requests, so zipfile can pull one layer (~70 MB) out of
    the 380 MB PRG package without downloading the rest."""

    def __init__(self, client: httpx.Client, url: str):
        self.client, self.url, self.pos = client, url, 0
        response = client.head(url, follow_redirects=True)
        response.raise_for_status()
        self.size = int(response.headers["content-length"])

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n=-1):
        end = self.size - 1 if n is None or n < 0 else min(self.size - 1, self.pos + n - 1)
        if self.pos > end:
            return b""
        response = self.client.get(self.url, headers={"Range": f"bytes={self.pos}-{end}"}, follow_redirects=True)
        response.raise_for_status()
        self.pos += len(response.content)
        return response.content


def download(dest: Path, url: str = PRG_URL) -> Path:
    """Extract the cadastral-unit layer from the PRG package into `dest`; returns the shapefile path (no suffix)."""
    dest.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": settings.HTTP_USER_AGENT}
    with httpx.Client(timeout=120, headers=headers) as client:
        archive = zipfile.ZipFile(RemoteFile(client, url))
        for member in archive.namelist():
            if member.startswith(LAYER) and not member.endswith(".qmd"):
                logger.info("Downloading %s", member)
                archive.extract(member, dest)
    return dest / LAYER


def load(shapefile_path: Path) -> int:
    """Replace the AdminUnit table with the units in a PRG A05 shapefile (ETRS89). Returns the number of units."""
    import shapefile  # pyshp: pure Python, no GDAL

    reader = shapefile.Reader(str(shapefile_path), encoding="utf-8")
    rows = []
    for shape_record in reader.iterShapeRecords():
        record = shape_record.record.as_dict()
        version = (record.get("IIP_WERSJA") or record.get("WERSJA_OD") or "")[:10]
        rows.append(
            {
                "code": record["JPT_KOD_JE"],
                "name": record["JPT_NAZWA_"],
                **unit_values(record["JPT_KOD_JE"], record["JPT_NAZWA_"]),
                "version": version or None,
                "geojson": json.dumps(shape_record.shape.__geo_interface__),
            }
        )
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("DELETE FROM devices_adminunit")
        insert_units(cursor, rows)
    return len(rows)


def insert_units(cursor, rows: list[dict], srid: int = 4258) -> None:
    """Insert units given as GeoJSON in `srid` (PRG ships ETRS89 = EPSG:4258), stored in PUWG 1992 (EPSG:2180)."""
    sql = """
        INSERT INTO devices_adminunit (code, name, teryt, city, municipality, version, geom)
        VALUES (%(code)s, %(name)s, %(teryt)s, %(city)s, %(municipality)s, %(version)s,
                ST_Multi(ST_CollectionExtract(ST_MakeValid(
                    ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%(geojson)s), %(srid)s), 2180)), 3)))
    """
    for row in rows:
        cursor.execute(sql, row | {"srid": srid})


def loaded() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM devices_adminunit)")
        return cursor.fetchone()[0]


def lookup(points: list[tuple[str, float, float]], margin_m: float = BORDER_MARGIN_M) -> dict[str, dict]:
    """(id, lat, lon) → {"teryt", "city", "version"} for points inside a unit. `teryt` or `city` is None when the
    point's unit has none (rural area) or a unit within `margin_m` says otherwise (too close to a boundary)."""
    if not points:
        return {}
    payload = json.dumps([{"id": i, "lat": lat, "lon": lon} for i, lat, lon in points if lat is not None])
    sql = """
        WITH p AS (
            SELECT x.id, ST_Transform(ST_SetSRID(ST_MakePoint(x.lon, x.lat), 4326), 2180) AS g
            FROM jsonb_to_recordset(%(points)s::jsonb) AS x(id text, lat float8, lon float8)
        )
        SELECT p.id, u.teryt, u.city, u.version,
               NOT EXISTS (SELECT 1 FROM devices_adminunit o
                           WHERE ST_DWithin(o.geom, p.g, %(margin)s) AND o.teryt <> u.teryt) AS teryt_sure,
               NOT EXISTS (SELECT 1 FROM devices_adminunit o
                           WHERE ST_DWithin(o.geom, p.g, %(margin)s) AND o.city IS DISTINCT FROM u.city) AS city_sure
        FROM p JOIN devices_adminunit u ON ST_Intersects(u.geom, p.g)
    """
    found: dict[str, dict] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, {"points": payload, "margin": margin_m})
        for point_id, teryt, city, version, teryt_sure, city_sure in cursor.fetchall():
            hit = {
                "teryt": teryt if teryt_sure else None,
                "city": city if city_sure else None,
                "version": version.isoformat() if isinstance(version, date) else None,
            }
            if point_id in found:  # exactly on a boundary: keep only what both units agree on
                previous = found[point_id]
                hit = {k: hit[k] if hit[k] == previous[k] else None for k in hit}
            found[point_id] = hit
    return found


def municipality(teryt: str | None) -> str | None:
    """Display name of the municipality with this TERYT code ('gmina wiejska Zawoja'), when boundaries are loaded."""
    if not teryt:
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT municipality FROM devices_adminunit WHERE teryt = %s LIMIT 1", [teryt])
        row = cursor.fetchone()
    return row[0] if row else None
