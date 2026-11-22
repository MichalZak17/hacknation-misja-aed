"""Legionowo: a CSV with TERC/SIMC codes and the address split into parts, but no device ID."""

import hashlib

from ..base import Connector
from ..common import CC0, STREET_PREFIXES, clean, join_address, read_csv


class LegionowoConnector(Connector):
    key = "legionowo_csv"
    label = "Legionowo (CSV z TERC/SIMC)"
    format = "csv"
    priority = 50
    default_integration = {
        "slug": "legionowo",
        "name": "Legionowo — AED",
        "publisher": "Gmina Miejska Legionowo",
        "source_url": "https://api.dane.gov.pl/media/resources/20260914/aed.csv",
        "homepage_url": "https://api.dane.gov.pl/1.4/datasets/40593",
        "attribution": "Gmina Miejska Legionowo",
        "config": {"bounds": [52.37, 20.87, 52.44, 20.99], "teryt": "1408011"},
        "description": "Brak identyfikatora urządzenia: klucz to skrót nazwy i adresu (zmiana adresu = nowy rekord).",
        **CC0,
    }

    def parse(self, raw):
        for row in read_csv(raw, delimiter=","):
            prefix = STREET_PREFIXES.get((row.get("cecha_ulicy") or "").lower(), clean(row.get("cecha_ulicy")))
            street = clean(" ".join(x for x in [prefix, row.get("nazwa_ulicy")] if x))
            address = join_address(street, row.get("nr_budynku"), row.get("nr_lokalu"))
            data = {
                "building_name": clean(row.get("nazwa")),
                "address": address,
                "postal_code": clean(row.get("kod_pocztowy")),
                "city": clean(row.get("miejscowosc")),
                "simc": clean(row.get("kod_simc")),
            }
            # No device ID in the file: derive one from name + address (a changed address is a new record)
            key = "|".join([clean(row.get("nazwa")) or "", address or ""]).lower()
            source_id = "h-" + hashlib.sha1(key.encode()).hexdigest()[:12]
            lat, lon = row.get("szerokosc_geograficzna"), row.get("dlugosc_geograficzna")
            yield self.record(source_id, lat, lon, data, raw=row, issues=["derived_id"])
