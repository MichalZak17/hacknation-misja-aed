"""Operator import: an AED owner's CSV or XLSX in the reference schema (devices/schema.py). Columns may be the field
names (`serial_number`) or the Polish labels (`Numer seryjny`), so the reference scope template (schema.xlsx or
schema-template.csv) uploads as is once filled in; its example rows (PRZYKLAD-…) are skipped. Access conditions
come as one list column (`access_conditions`, values separated by ";") or as the template's true/false column per
condition (`access_conditions_key_holder` / „Warunek dostępu: …”). This is the only way
hardware, pads, battery and upkeep data enter today — none of the open feeds publish it.
"""

import io
from datetime import UTC, datetime
from pathlib import Path

from django.utils import timezone

from devices.reference_scope import EXAMPLE_PREFIX
from devices.schema import (
    ALLOWED_VALUES,
    BOOL_FIELDS,
    DATE_FIELDS,
    DATETIME_FIELDS,
    ENUM_FIELDS,
    FLOAT_FIELDS,
    LIST_FIELDS,
    MERGE_FIELDS,
    SCHEMA,
    list_columns,
)

from ..base import Connector, ConnectorError
from ..common import clean, iso, join_address, read_csv, to_bool, to_date, to_float

ALIASES = {f.field.lower(): f.field for f in SCHEMA} | {f.label.lower(): f.field for f in SCHEMA}
ALIASES |= {"source_id": "id", "identyfikator": "id", "latitude": "lat", "longitude": "lon", "szerokość": "lat"}
ALIASES |= {"długość": "lon"}
# A list field given as one true/false column per value (the template's "Warunek dostępu: …" columns)
LIST_COLUMNS = {
    alias.lower(): (field, value)
    for field in LIST_FIELDS
    for name, label, value in list_columns(field)
    for alias in (name, label)
}
CODE_LENGTHS = {"teryt": 7, "simc": 7}  # a spreadsheet that typed the code as a number dropped its leading zero


class OperatorFileConnector(Connector):
    key = "operator_file"
    label = "Import dysponenta (CSV/XLSX wg wzorcowego zakresu)"
    format = "csv/xlsx"
    accepts_upload = True
    # Operators are the only source of hardware and upkeep data, so they outrank every open feed
    priority = 90
    # A file only changes when someone uploads a new one
    periodic = False
    default_integration = None  # created per operator from the UI

    @property
    def snapshot_extension(self) -> str:
        return Path(self.config.get("file_path", "upload.csv")).suffix.lstrip(".") or "csv"

    def fetch(self) -> bytes:
        path = self.config.get("file_path")
        if not path or not Path(path).exists():
            raise ConnectorError("No file uploaded yet: upload a CSV or XLSX first")
        return Path(path).read_bytes()

    def _rows(self, raw: bytes) -> list[dict]:
        if raw[:2] == b"PK":  # XLSX is a zip
            from openpyxl import load_workbook

            sheet = load_workbook(io.BytesIO(raw), read_only=True, data_only=True).worksheets[0]
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return []
            header = [str(h).strip() if h is not None else "" for h in rows[0]]
            return [
                {header[i]: v for i, v in enumerate(row) if i < len(header) and header[i]}
                for row in rows[1:]
                if any(v not in (None, "") for v in row)
            ]
        return read_csv(raw)

    def parse(self, raw):
        for number, row in enumerate(self._rows(raw), start=2):
            values = {}
            flags: dict[str, list[str]] = {}  # list field → values whose true/false column is true
            for column, value in row.items():
                key = str(column).strip().lower()
                field = ALIASES.get(key)
                if field:
                    values[field] = value
                elif key in LIST_COLUMNS:
                    field, item = LIST_COLUMNS[key]
                    flags.setdefault(field, [])
                    if to_bool(value):
                        flags[field].append(item)
            for field, items in flags.items():  # merged with the single list column, if the file has both
                values[field] = ";".join([str(values.get(field) or ""), *items])
            if str(values.get("id") or "").startswith(EXAMPLE_PREFIX):
                continue  # the template's example rows, left in by mistake
            issues = []
            source_id = (
                clean(values.get("id")) or clean(values.get("serial_number")) or clean(values.get("inventory_number"))
            )
            if not source_id:
                source_id = f"row-{number}"
                issues.append("missing_id")
            data = {}
            for field in MERGE_FIELDS:
                if field not in values:
                    continue
                value = values[field]
                if field in DATE_FIELDS:
                    parsed = to_date(value)
                    if value not in (None, "") and parsed is None:
                        issues.append(f"bad_date:{field}")
                    data[field] = iso(parsed)
                elif field in DATETIME_FIELDS:
                    parsed = to_datetime(value)
                    if value not in (None, "") and parsed is None:
                        issues.append(f"bad_date:{field}")
                    data[field] = parsed
                elif field in BOOL_FIELDS:
                    data[field] = to_bool(value)
                elif field in FLOAT_FIELDS:
                    data[field] = to_float(value)
                elif field in LIST_FIELDS:
                    items = [x for x in (clean(v) for v in str(value or "").replace(",", ";").split(";")) if x]
                    allowed = {v for v, _ in ALLOWED_VALUES[field]}
                    if any(x not in allowed for x in items):
                        issues.append(f"bad_value:{field}")
                    data[field] = [x for x in dict.fromkeys(items) if x in allowed] or None
                elif field in CODE_LENGTHS and isinstance(value, int):
                    data[field] = str(value).zfill(CODE_LENGTHS[field])
                elif field in ENUM_FIELDS:
                    text = (clean(value) or "").lower()
                    if text and text not in ENUM_FIELDS[field] and text != "unknown":
                        issues.append(f"bad_value:{field}")
                    data[field] = text if text in ENUM_FIELDS[field] else None
                else:
                    data[field] = clean(value)
            if not data.get("address"):  # the address given in parts (street_type, street, house_number)
                street = " ".join(x for x in (clean(values.get("street_type")), clean(values.get("street"))) if x)
                data["address"] = join_address(street, values.get("house_number"))
            yield self.record(source_id, values.get("lat"), values.get("lon"), data, raw=_jsonable(row), issues=issues)


def to_datetime(value) -> str | None:
    """ISO 8601 date and time (or a date alone, or DD.MM.YYYY), stored in UTC. Without an offset it is Polish local
    time, which is what a spreadsheet holds."""
    parsed = value if isinstance(value, datetime) else None
    if parsed is None:
        text = clean(value)
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            day = to_date(text) if len(text) == 10 else None
            if day is None:
                return None
            parsed = datetime(day.year, day.month, day.day)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed.astimezone(UTC).isoformat()


def _jsonable(row: dict) -> dict:
    """XLSX cells come back as dates and datetimes; the raw payload is stored as JSON."""
    return {str(k): (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
