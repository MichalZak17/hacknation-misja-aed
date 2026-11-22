"""Przemyśl: the city's skyCMS GeoJSON export, listed on dane.gov.pl."""

from ..base import Connector
from ..common import CC0, clean, geojson_features, join_address


class PrzemyslConnector(Connector):
    key = "przemysl_geojson"
    label = "Przemyśl (GeoJSON, skyCMS)"
    format = "geojson"
    priority = 50
    default_integration = {
        "slug": "przemysl",
        "name": "Przemyśl — defibrylatory AED",
        "publisher": "Gmina Miejska Przemyśl",
        "source_url": "https://przemysl.skycms.com.pl/open-data/20/1730818801_b50R6UVxPgoVdBbq/geojson",
        "homepage_url": "https://api.dane.gov.pl/1.4/datasets/4581",
        "attribution": "Gmina Miejska Przemyśl",
        "config": {"bounds": [49.73, 22.66, 49.84, 22.88], "teryt": "1862011"},
        "description": "Klucz: properties.id. Katalog deklaruje CC0 1.0 i codzienną aktualizację.",
        **CC0,
    }

    def parse(self, raw):
        for p, lat, lon in geojson_features(raw):
            gallery = p.get("gallery") or []
            data = {
                "building_name": clean(p.get("name")),
                "address": join_address(p.get("street"), p.get("home_number")),
                "postal_code": clean(p.get("postcode")),
                "city": clean(p.get("city")),
                "photo_url": gallery[0].get("url") if gallery and isinstance(gallery[0], dict) else None,
            }
            yield self.record(p.get("id"), lat, lon, data, raw=p)
