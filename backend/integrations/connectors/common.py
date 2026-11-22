"""Small normalisation helpers shared by connectors. They never invent a value: anything they can't read is None."""

import csv
import io
import json
import re
from datetime import date, datetime


class ConnectorError(Exception):
    """The source could not be fetched or read — a technical failure, never a data result."""


CC0 = {"license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
CC_BY = {"license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/"}

POSTAL_CITY = re.compile(r"(\d{2}-\d{3})\s+(.+)$")
STREET_PREFIXES = {"ulica": "ul.", "aleja": "al.", "plac": "pl.", "osiedle": "os.", "rondo": "rondo", "skwer": "skwer"}


def clean(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


_OH_TOKEN = re.compile(
    r'"[^"]*"'  # comments are part of the syntax
    r"|24/7"
    r"|\d{1,2}:\d{2}\+?"
    r"|\b(?:Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b(?:\s+\d{1,2}\b(?!:))?"
    r"|\bweek\s+\d{1,2}(?:-\d{1,2})?(?:/\d+)?"
    r"|\b(?:19|20)\d{2}\b"
    r"|\[\s*-?\d+(?:\s*-\s*\d+)?(?:\s*,\s*-?\d+(?:\s*-\s*\d+)?)*\s*\]"
    r"|\b(?:off|closed|open|unknown|sunrise|sunset|dawn|dusk|easter)\b"
)
_OH_REST = re.compile(r"^[\s;,\-|/+():]*$")
_OH_RULE = re.compile(r"\d{1,2}:\d{2}|24/7|\boff\b|\bclosed\b")


def is_opening_hours(value) -> bool:
    """Whether a string reads as OSM `opening_hours` syntax ("Mo-Fr 07:30-15:30; Sa-Su, PH off", "24/7") rather than
    prose ("W godzinach pracy urzędu", "24h", "7-21:30"). A lexical check, not a full parser: every part must be a
    known token, and there must be at least one time span, 24/7 or off."""
    text = clean(value)
    if not text:
        return False
    return bool(_OH_RULE.search(text)) and bool(_OH_REST.match(_OH_TOKEN.sub(" ", text)))


def to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


_FLOOR = re.compile(r"[+-]?\d{1,3}")


def to_floor(value) -> str | None:
    """A floor as the schema states it, a whole number ("-1", "0", "2"); "+1" and "01" read as "1". Anything else
    (a mezzanine "0.5", a range "0;1", "4 - klatka D") is not a floor number and gives None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = clean(value)
    return str(int(text)) if text and _FLOOR.fullmatch(text) else None


def with_floor(data: dict) -> dict:
    """Normalise `floor` to a whole number. A floor the source states some other way leaves `floor` empty and is kept
    in `location_detail` ("piętro: 0.5"), so the information stays readable without breaking the integer column."""
    raw = clean(data.get("floor"))
    if raw is None:
        return data
    floor = to_floor(raw)
    if floor is None:
        detail = clean(data.get("location_detail"))
        if not detail or raw not in detail:
            data["location_detail"] = f"{detail}; piętro: {raw}" if detail else f"piętro: {raw}"
    data["floor"] = floor
    return data


def to_bool(value) -> bool | None:
    text = (clean(value) or "").lower()
    if text in {"yes", "true", "1", "tak", "t", "y"}:
        return True
    if text in {"no", "false", "0", "nie", "n"}:
        return False
    return None


def to_date(value) -> date | None:
    """ISO dates and Polish DD.MM.YYYY. Partial dates (2024-05) are not dates and give None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1250", "iso-8859-2"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ConnectorError("Unreadable text encoding")


def read_csv(raw: bytes | str, delimiter: str | None = None) -> list[dict]:
    """Rows as dicts with trimmed header names and values."""
    text = raw if isinstance(raw, str) else decode(raw)
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return []
    header = [h.strip().lstrip("﻿") for h in rows[0]]
    return [
        {header[i]: cell.strip() for i, cell in enumerate(row) if i < len(header)}
        for row in rows[1:]
        if any(cell.strip() for cell in row)
    ]


def read_json(raw: bytes):
    try:
        return json.loads(decode(raw))
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"Invalid JSON: {exc}") from exc


def geojson_features(raw: bytes) -> list[tuple[dict, float | None, float | None]]:
    """(properties, lat, lon) for every feature of a FeatureCollection. GeoJSON stores [lon, lat]."""
    payload = read_json(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ConnectorError("Not a GeoJSON FeatureCollection (no `features` list)")
    out = []
    for feature in payload["features"]:
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        lon, lat = (coords[0], coords[1]) if len(coords) >= 2 else (None, None)
        out.append((feature.get("properties") or {}, to_float(lat), to_float(lon)))
    return out


# Source wording for `access` → the reference enum. OSM tags and Polish municipal registers.
ACCESS = {
    "yes": "public",
    "permissive": "public",
    "publiczny": "public",
    "customers": "limited",
    "permit": "limited",
    "private": "private",
    "no": "private",
    "prywatny": "private",
}


def to_access(value) -> str | None:
    return ACCESS.get((clean(value) or "").lower())


def split_postal(address: str | None) -> tuple[str | None, str | None, str | None]:
    """'ul. Jasna 1, 38-400 Krosno' → ('ul. Jasna 1', '38-400', 'Krosno')."""
    if not address:
        return None, None, None
    parts = [p.strip() for p in address.split(",")]
    street, postal, city = parts[0], None, None
    for part in parts[1:]:
        match = POSTAL_CITY.search(part)
        if match:
            postal, city = match.group(1), match.group(2).strip()
    return clean(street), postal, clean(city)


def join_address(street: str | None, number: str | None, unit: str | None = None) -> str | None:
    street = clean(street)
    if not street:
        return None
    number = clean(number)
    unit = clean(unit)
    return f"{street} {number}{'/' + unit if unit else ''}" if number else street


def compact(data: dict) -> dict:
    """Drop None so stored records only state what the source states."""
    return {k: v for k, v in data.items() if v is not None}


def validate_bounds(bounds) -> list[str]:
    """`config.bounds` must be [min_lat, min_lon, max_lat, max_lon] with min < max, or absent."""
    if bounds is None:
        return []
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in bounds)
    ):
        return ["bounds: oczekiwano [min_lat, min_lon, max_lat, max_lon]"]
    min_lat, min_lon, max_lat, max_lon = bounds
    if not (min_lat < max_lat and min_lon < max_lon):
        return ["bounds: minimum musi być mniejsze od maksimum"]
    return []
