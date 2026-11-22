"""Warsaw 19115 AED register, through the city's public ArcGIS snapshot (GeoJSON, outSR=4326)."""

import json
from functools import cache
from pathlib import Path

from devices.address import STREET_TYPES

from ..base import Connector
from ..common import CC_BY, clean, geojson_features, join_address, to_access


@cache
def _street_types() -> dict:
    """Street name → prefix (cecha), from the city's own address register (same publisher): the 19115 feed writes
    "Suwalska", the register "ulica Suwalska". Built once from dane.gov.pl dataset 469 (adres uniwersalny); only names
    whose prefix is unambiguous are in it, so a miss leaves the prefix empty rather than guessing "ul."."""
    return json.loads((Path(__file__).parent / "street_types.json").read_text())


def street_type(street: str | None) -> str | None:
    """'Suwalska' → 'ul.'; 'K. Szajnochy' → 'ul.' (by the unambiguous last word); a street that already starts with
    a prefix ('al. Krakowska') or is unknown → None."""
    name = " ".join((street or "").split())
    if not name or name.split(" ")[0].lower() in STREET_TYPES:
        return None
    lookup = _street_types()
    key = name.lower().replace("„", "").replace("”", "").replace('"', "")
    return lookup["names"].get(key) or lookup["last_words"].get(key.split(" ")[-1])


def full_street(street: str | None) -> str | None:
    prefix = street_type(street)
    return f"{prefix} {' '.join(street.split())}" if prefix else street


class WarsawConnector(Connector):
    key = "warsaw_arcgis"
    label = "Warszawa 19115 (ArcGIS GeoJSON)"
    format = "geojson"
    priority = 60
    default_integration = {
        "slug": "warszawa-19115",
        "name": "Warszawa 19115 / Otwarte dane Warszawy",
        "publisher": "Miasto Stołeczne Warszawa",
        "source_url": (
            "https://services.arcgis.com/zg6BBB0wvjzrRBLk/arcgis/rest/services/AED/FeatureServer/0/query"
            "?where=1%3D1&outFields=%2A&outSR=4326&f=geojson"
        ),
        "homepage_url": "https://api.dane.gov.pl/1.4/datasets/39512",
        "attribution": "Miasto Stołeczne Warszawa, warszawa19115.pl",
        "config": {"bounds": [52.09, 20.85, 52.37, 21.28], "teryt": "1465011"},
        "description": "Rejestr miejski AED. Klucz: defib_id. OSM odwołuje się do niego tagiem ref:api-um-warszawa-pl.",
        **CC_BY,
    }

    def parse(self, raw):
        for p, lat, lon in geojson_features(raw):
            device_loc = (p.get("device_loc") or "").lower()
            indoor = (
                True if device_loc.startswith("wewnątrz") else False if device_loc.startswith("na zewnątrz") else None
            )
            data = {
                "building_name": clean(p.get("object_name")),
                "address": join_address(full_street(p.get("street")), p.get("building_no")),
                "postal_code": clean(p.get("postcode")),
                "city": clean(p.get("city")),
                "location_detail": "; ".join(
                    x for x in [clean(p.get("location_desc")), clean(p.get("device_loc"))] if x
                )
                or None,
                "indoor": indoor,
                "access": to_access(p.get("public_access")),
                "opening_hours_raw": clean(p.get("access_desc")),
                "manufacturer": clean(p.get("manufacturer")),
            }
            # Some snapshots carry the point only in the attributes
            lat = lat if lat is not None else p.get("latitude")
            lon = lon if lon is not None else p.get("longitude")
            yield self.record(p.get("defib_id"), lat, lon, data, raw=p)
