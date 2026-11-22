"""Reference scope per source (zakres referencyjny źródeł): for every field of the reference record (schema.py), how
many of each source's live records state it, and how much of the merged dataset has it filled and from where.

A value counts as filled unless it is None, an empty string, an empty list or "unknown". Source columns read the
normalised `SourceRecord.data` (what the source itself states, not what the LLM inferred from its free text); the
merged column reads the active Devices and breaks each field down by `field_sources` (source and method: inferred,
geocoded). Fields the merge assigns itself (id, readiness, sources) do not apply to a single source.
"""

from collections import Counter, defaultdict

from django.utils import timezone

from integrations.models import Integration, SourceRecord

from .address import split_address
from .cache import data_version
from .models import Device
from .schema import ADDRESS_PART_FIELDS, SCHEMA

LEVELS = [
    {"level": 1, "label": "Podstawowy"},
    {"level": 2, "label": "Rozszerzony"},
    {"level": 3, "label": "Pełny"},
]
# Set by the merge, never by a source
MERGE_ONLY_FIELDS = {"id", "readiness", "sources"}
# Where field_sources keeps the provenance of a field that has no entry of its own
PROVENANCE_OF = {"lon": "lat"} | dict.fromkeys(ADDRESS_PART_FIELDS, "address")
ADDRESS_PART_INDEX = {"street_type": 0, "street": 1, "house_number": 2}


def is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value != "unknown"
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _cell(count: int, total: int) -> dict:
    return {"count": count, "pct": round(100 * count / total, 1) if total else None}


def _source_counts() -> tuple[dict[int, int], dict[int, Counter]]:
    """(live records per integration id, filled count per integration id and field)."""
    totals: Counter = Counter()
    filled: dict[int, Counter] = defaultdict(Counter)
    rows = SourceRecord.objects.filter(removed_at__isnull=True, is_valid=True).values_list(
        "integration_id", "lat", "lon", "data"
    )
    for integration_id, lat, lon, data in rows.iterator(chunk_size=5000):
        totals[integration_id] += 1
        counts = filled[integration_id]
        if lat is not None:
            counts["lat"] += 1
        if lon is not None:
            counts["lon"] += 1
        data = data or {}
        for key, value in data.items():
            if is_filled(value):
                counts[key] += 1
        if is_filled(data.get("address")):
            parts = split_address(data["address"])
            for field, index in ADDRESS_PART_INDEX.items():
                if parts[index]:
                    counts[field] += 1
    return totals, filled


def _merged_counts() -> tuple[int, Counter, dict[str, Counter]]:
    """(active devices, filled count per field, provenance (source, method) counts per field)."""
    columns = [f.field for f in SCHEMA if f.field not in ADDRESS_PART_FIELDS]
    total = 0
    filled: Counter = Counter()
    provenance: dict[str, Counter] = defaultdict(Counter)
    rows = Device.objects.filter(active=True, merged_into__isnull=True).values_list(*columns, "field_sources")
    for row in rows.iterator(chunk_size=5000):
        total += 1
        values = dict(zip(columns, row[:-1], strict=True))
        field_sources = row[-1] or {}
        parts = split_address(values["address"])
        values |= {field: parts[index] for field, index in ADDRESS_PART_INDEX.items()}
        for field, value in values.items():
            # is_mobile defaults to False when no source states it
            if field == "is_mobile" and field not in field_sources:
                continue
            if not is_filled(value):
                continue
            filled[field] += 1
            origin = field_sources.get(PROVENANCE_OF.get(field, field))
            if origin:
                provenance[field][(origin.get("source", ""), origin.get("method", "source"))] += 1
    return total, filled, provenance


def coverage() -> dict:
    integrations = list(Integration.objects.filter(enabled=True).order_by("-priority", "name"))
    totals, source_filled = _source_counts()
    merged_total, merged_filled, provenance = _merged_counts()

    fields = []
    for f in SCHEMA:
        by_source = {}
        for integration in integrations:
            if f.field in MERGE_ONLY_FIELDS:
                by_source[integration.slug] = None
            else:
                by_source[integration.slug] = _cell(source_filled[integration.pk][f.field], totals[integration.pk])
        merged = _cell(merged_filled[f.field], merged_total) | {
            "by_source": [
                {"source": source, "method": method, "count": n}
                for (source, method), n in provenance[f.field].most_common()
            ]
        }
        fields.append({"field": f.field, "label": f.label, "level": f.level, "sources": by_source, "merged": merged})

    return {
        "levels": LEVELS,
        "sources": [
            {
                "slug": i.slug,
                "name": i.name,
                "publisher": i.publisher,
                "priority": i.priority,
                "records": totals[i.pk],
            }
            for i in integrations
        ],
        "merged": {"records": merged_total},
        "fields": fields,
        "data_version": data_version(),
        "generated_at": timezone.now().isoformat(),
    }
