"""Krosno: a CSV on dane.gov.pl with spaces in its header names. Marki publishes the same columns."""

from ..base import Connector
from ..common import CC0, clean, read_csv, split_postal


class KrosnoStyleCsvConnector(Connector):
    """`Długość geograficzna, Szerokość geograficzna, Nazwa, Lokalizacja, Adres, Numer Id` (Krosno and Marki)."""

    key = "krosno_csv"
    label = "Krosno (CSV)"
    format = "csv"
    priority = 50
    default_integration = {
        "slug": "krosno",
        "name": "Krosno — defibrylatory",
        "publisher": "Gmina Miasto Krosno",
        "source_url": "https://api.dane.gov.pl/media/resources/20240219/Defibrylator_jAmxQcp.csv",
        "homepage_url": "https://api.dane.gov.pl/1.4/datasets/3624",
        "attribution": "Gmina Miasto Krosno",
        "config": {"bounds": [49.64, 21.66, 49.75, 21.85], "teryt": "1861011"},
        "description": "Kolumny z odstępami w nagłówku. Metadane katalogu z 2024 r.",
        **CC0,
    }

    def rows(self, raw) -> list[dict]:
        return read_csv(raw, delimiter=",")

    def parse(self, raw):
        for row in self.rows(raw):
            # The header says longitude first; validation swaps (and flags) rows that are really lat, lon
            street, postal, city = split_postal(row.get("Adres"))
            data = {
                "building_name": clean(row.get("Lokalizacja")),
                "address": street,
                "postal_code": postal,
                "city": city,
            }
            lat, lon = row.get("Szerokość geograficzna"), row.get("Długość geograficzna")
            yield self.record(row.get("Numer Id"), lat, lon, data, raw=row)
