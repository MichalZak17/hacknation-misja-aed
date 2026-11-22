"""OpenAEDMap Poland: every `emergency=defibrillator` node in OpenStreetMap, as GeoJSON."""

from ..base import Connector
from ..common import clean, geojson_features, is_opening_hours, iso, join_address, to_access, to_bool, to_date

# Tags the LLM reads: the free text, plus the structured tags it may copy or correct. Same set as the benchmark
# (scripts/llm_bench/common.py), so its scores apply.
TEXT_TAGS = (
    "defibrillator:location:pl",
    "defibrillator:location",
    "defibrillator:location:en",
    "description",
    "description:pl",
    "note",
    "fixme",
    "location",
)
CONTEXT_TAGS = ("opening_hours", "level", "indoor", "access")


class OsmConnector(Connector):
    key = "openaedmap"
    label = "OpenAEDMap (OpenStreetMap) GeoJSON"
    format = "geojson"
    priority = 10
    record_url_template = "https://www.openstreetmap.org/{id}"  # source_record_id is "node/123"
    default_integration = {
        "slug": "osm-poland",
        "name": "OpenAEDMap Polska / OpenStreetMap",
        "publisher": "OpenStreetMap contributors (OpenAEDMap)",
        "source_url": "https://openaedmap.org/api/v1/countries/PL.geojson",
        "homepage_url": "https://openstreetmap.org.pl/2022/mapa-defibrylatorow-aed-na-terenie-polski/",
        "license": "ODbL 1.0",
        "license_url": "https://www.openstreetmap.org/copyright",
        "attribution": "© OpenStreetMap contributors",
        "description": "Ogólnopolska warstwa AED z OpenStreetMap. Klucz: @osm_type/@osm_id.",
    }

    def parse(self, raw):
        for props, lat, lon in geojson_features(raw):
            issues = []
            check_date = to_date(props.get("check_date"))
            if props.get("check_date") and not check_date:
                issues.append("check_date_not_a_full_date")
            location = (
                props.get("defibrillator:location:pl")
                or props.get("defibrillator:location")
                or props.get("location")
                or props.get("description")
            )
            image = clean(props.get("image"))
            hours = clean(props.get("opening_hours"))
            refs = {}
            if props.get("ref:api-um-warszawa-pl"):
                refs["warszawa-19115"] = str(props["ref:api-um-warszawa-pl"]).strip()
            data = {
                "building_name": clean(props.get("name")),
                "location_detail": clean(location),
                "address": join_address(
                    props.get("addr:street") or props.get("addr:place"), props.get("addr:housenumber")
                ),
                "postal_code": clean(props.get("addr:postcode")),
                "city": clean(props.get("addr:city")),
                "simc": clean(props.get("addr:city:simc")),
                "indoor": to_bool(props.get("indoor")),
                "floor": clean(props.get("level") or props.get("addr:floor") or props.get("floor")),
                "access": to_access(props.get("access")),
                # Prose in the tag ("Całodobowo", "W godzinach pracy urzędu") stays in _raw; the LLM may convert it
                "opening_hours": hours if is_opening_hours(hours) else None,
                "opening_hours_raw": hours,
                "operator_name": clean(props.get("operator")),
                "manufacturer": clean(props.get("manufacturer")),
                "model": clean(props.get("model")),
                "is_mobile": True if to_bool(props.get("mobile")) else None,
                "photo_url": image if image and image.startswith("http") else None,
                "verified_on": iso(check_date),
                "verification_method": "OSM check_date" if check_date else None,
            }
            osm_id = f"{props.get('@osm_type', 'node')}/{props.get('@osm_id')}"
            yield self.record(osm_id, lat, lon, data, raw=props, issues=issues, refs=refs)

    def text_input(self, record):
        raw = record.raw
        hours = raw.get("opening_hours")
        if not any(raw.get(k) for k in TEXT_TAGS) and not (hours and not is_opening_hours(hours)):
            return None
        return {k: raw[k] for k in TEXT_TAGS + CONTEXT_TAGS if raw.get(k)}
