"""AED coverage per voivodeship or municipality (gmina): counts, density per 100 km², and the units with no AED at all.

Units and their areas come from the PRG boundaries (`devices_adminunit`, stored in PUWG 1992 so ST_Area is in m²);
devices are counted by their `teryt` (stated by a source, or filled from the coordinates, see boundaries.py). A
municipality's TERYT code is 7 digits: voivodeship (2) + county (2) + municipality (2) + kind (1).
"""

from collections import defaultdict

from django.core.cache import cache
from django.db import connection

VOIVODESHIPS = {
    "02": "dolnośląskie",
    "04": "kujawsko-pomorskie",
    "06": "lubelskie",
    "08": "lubuskie",
    "10": "łódzkie",
    "12": "małopolskie",
    "14": "mazowieckie",
    "16": "opolskie",
    "18": "podkarpackie",
    "20": "podlaskie",
    "22": "pomorskie",
    "24": "śląskie",
    "26": "świętokrzyskie",
    "28": "warmińsko-mazurskie",
    "30": "wielkopolskie",
    "32": "zachodniopomorskie",
}
LEVELS = {"voivodeship": 2, "municipality": 7}
ACCESS = ["public", "limited", "private", "unknown"]


def municipality_areas() -> dict[str, tuple[str, float]]:
    """Municipality TERYT → (display name, area in km²) from the PRG boundaries; empty when they are not loaded.
    ST_Area over ~3,200 polygons takes seconds, so the result is cached until the boundaries are reloaded."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*), max(version) FROM devices_adminunit")
        count, version = cursor.fetchone()
    if not count:
        return {}

    def build():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT teryt, min(municipality), sum(ST_Area(geom)) / 1e6 FROM devices_adminunit GROUP BY teryt"
            )
            return {teryt: (name, area) for teryt, name, area in cursor.fetchall()}

    return cache.get_or_set(f"municipality-areas:{count}:{version}", build, timeout=None)


def _units(length: int, voivodeship: str | None) -> dict[str, dict]:
    """code → {name, area_km2} of the units at this level (by TERYT prefix length)."""
    areas: dict[str, float] = defaultdict(float)
    names: dict[str, str] = {}
    for teryt, (name, area) in municipality_areas().items():
        if voivodeship and not teryt.startswith(voivodeship):
            continue
        areas[teryt[:length]] += area
        names[teryt[:length]] = VOIVODESHIPS.get(teryt[:2]) if length == 2 else name
    return {code: {"name": names[code], "area_km2": round(area, 1)} for code, area in areas.items()}


def _counts(length: int, voivodeship: str | None) -> dict[str, dict]:
    where, params = "", {"length": length}
    if voivodeship:
        where, params["prefix"] = "AND teryt LIKE %(prefix)s", f"{voivodeship}%"
    access_columns = ", ".join(f"count(*) FILTER (WHERE access = '{a}')" for a in ACCESS)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT left(teryt, %(length)s), count(*), {access_columns},
                   count(*) FILTER (WHERE opening_hours = '24/7'),
                   count(*) FILTER (WHERE opening_hours = '24/7' AND access = 'public'),
                   count(*) FILTER (WHERE verified_on IS NOT NULL)
            FROM devices_device
            WHERE active AND teryt IS NOT NULL {where}
            GROUP BY 1
            """,
            params,
        )
        rows = cursor.fetchall()
    out = {}
    for code, total, *rest in rows:
        by_access, (open_24_7, public_24_7, verified) = dict(zip(ACCESS, rest[: len(ACCESS)], strict=True)), rest[4:]
        out[code] = {
            "devices": total,
            "by_access": by_access,
            "open_24_7": open_24_7,
            "public_24_7": public_24_7,
            "verified": verified,
        }
    return out


def unlocated() -> int:
    """Active devices with no TERYT code (outside Poland's boundaries, or too close to one to be sure)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM devices_device WHERE active AND teryt IS NULL")
        return cursor.fetchone()[0]


def regions(level: str, voivodeship: str | None = None) -> list[dict]:
    """One row per unit, by code. Units known from the boundaries are listed even with no AED (devices 0)."""
    length = LEVELS[level]
    units, counts = _units(length, voivodeship), _counts(length, voivodeship)
    empty = {"devices": 0, "by_access": dict.fromkeys(ACCESS, 0), "open_24_7": 0, "public_24_7": 0, "verified": 0}
    rows = []
    for code in sorted(set(units) | set(counts)):
        unit = units.get(code, {"name": VOIVODESHIPS.get(code) if length == 2 else None, "area_km2": None})
        count = counts.get(code, empty)
        area = unit["area_km2"]
        rows.append(
            {
                "teryt": code,
                "name": unit["name"],
                **count,
                "area_km2": area,
                "per_100_km2": round(count["devices"] / area * 100, 2) if area else None,
            }
        )
    return rows
