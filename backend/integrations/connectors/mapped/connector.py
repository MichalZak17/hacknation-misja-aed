"""A config-only connector for plain GeoJSON/CSV/JSON feeds: map the source's columns onto schema fields in `config`.

{"format": "geojson",              # geojson | csv | json (a list of objects, or `items_path` into it)
 "id": "id", "lat": "lat", "lon": "lon",   # source keys (geojson takes coordinates from the geometry)
 "fields": {"building_name": "name", "address": "adres"},
 "constants": {"teryt": "2477011"},
 "items_path": "data.items",
 "bounds": [min_lat, min_lon, max_lat, max_lon]}   # optional; records outside are rejected

The config is written in code (a subclass with `default_integration`, see docs/integrations/mapped-feeds.mdx), not in the
admin UI: real feeds need joins, value maps and derived IDs that a column mapping can't express, so they get a class.
"""

from devices.schema import BOOL_FIELDS, DATE_FIELDS, MERGE_FIELDS

from ..base import Connector, ConnectorError
from ..common import clean, geojson_features, iso, read_csv, read_json, to_bool, to_date, to_float, validate_bounds

FORMATS = ("geojson", "csv", "json")


class MappedConnector(Connector):
    key = "mapped"
    label = "Mapowany GeoJSON/CSV/JSON (mapowanie kolumn w kodzie)"
    format = "configurable"
    # Above OSM, below city registers and operators. A subclass for a specific feed can declare its own.
    priority = 40
    default_config = {"format": "geojson", "id": "id", "lat": "lat", "lon": "lon", "fields": {}, "constants": {}}

    @property
    def snapshot_extension(self) -> str:
        return self.config.get("format", "json")

    def rows(self, raw) -> list[tuple[dict, float | None, float | None]]:
        """(source item, lat, lon). GeoJSON coordinates come from the geometry; CSV/JSON from the mapped columns."""
        fmt = self.config.get("format")
        lat_key, lon_key = self.config.get("lat"), self.config.get("lon")
        if fmt == "csv":
            return [(row, to_float(row.get(lat_key)), to_float(row.get(lon_key))) for row in read_csv(raw)]
        if fmt == "geojson":
            return geojson_features(raw)
        if fmt == "json":
            payload = read_json(raw)
            for part in filter(None, (self.config.get("items_path") or "").split(".")):
                payload = payload.get(part, []) if isinstance(payload, dict) else payload
            if not isinstance(payload, list):
                raise ConnectorError("items_path does not point at a list")
            return [
                (item, to_float(item.get(lat_key)), to_float(item.get(lon_key)))
                for item in payload
                if isinstance(item, dict)
            ]
        raise ConnectorError(f"Unknown format {fmt!r}")

    def parse(self, raw):
        errors = validate_config(self.config)
        if errors:
            raise ConnectorError("Invalid mapped config: " + "; ".join(errors))
        for item, lat, lon in self.rows(raw):
            data = dict(self.config.get("constants") or {})
            for field, source_key in (self.config.get("fields") or {}).items():
                value = item.get(source_key)
                if field in DATE_FIELDS:
                    data[field] = iso(to_date(value))
                elif field in BOOL_FIELDS:
                    data[field] = to_bool(value)
                else:
                    data[field] = clean(value)
            yield self.record(item.get(self.config["id"]), lat, lon, data, raw=item)


def validate_config(config: dict) -> list[str]:
    """Problems that would make every sync fail or reject every record; parse() refuses to run with any of them."""
    errors = []
    fmt = config.get("format")
    if fmt not in FORMATS:
        errors.append(f"format: wybierz jeden z {', '.join(FORMATS)}")
    if not isinstance(config.get("id"), str) or not config.get("id"):
        errors.append("id: wskaż kolumnę ze stałym identyfikatorem urządzenia")
    if fmt in {"csv", "json"}:
        for key in ("lat", "lon"):
            if not isinstance(config.get(key), str) or not config.get(key):
                errors.append(f"{key}: wskaż kolumnę ze współrzędną")
    fields = config.get("fields", {})
    if not isinstance(fields, dict) or not all(isinstance(v, str) and v for v in fields.values()):
        errors.append("fields: każde pole musi wskazywać kolumnę źródła")
    else:
        unknown = sorted(set(fields) - set(MERGE_FIELDS))
        if unknown:
            errors.append(f"fields: nieznane pola wzorcowe: {', '.join(unknown)}")
    constants = config.get("constants", {})
    if not isinstance(constants, dict):
        errors.append("constants: oczekiwano obiektu {pole: wartość}")
    else:
        unknown = sorted(set(constants) - set(MERGE_FIELDS))
        if unknown:
            errors.append(f"constants: nieznane pola wzorcowe: {', '.join(unknown)}")
    if config.get("items_path") is not None and not isinstance(config.get("items_path"), str):
        errors.append("items_path: oczekiwano tekstu, np. data.items")
    errors.extend(validate_bounds(config.get("bounds")))
    return errors
