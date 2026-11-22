"""Marki: Krosno's columns, but every line of the CSV is wrapped in another CSV."""

import csv
import io

from ..common import CC_BY, decode, read_csv
from ..krosno.connector import KrosnoStyleCsvConnector


class MarkiConnector(KrosnoStyleCsvConnector):
    """Each line of the outer CSV is one quoted field holding the real CSV line, and the coordinate columns hold
    latitude then longitude despite the header (the engine's swap check fixes and flags it)."""

    key = "marki_csv"
    label = "Marki (CSV w CSV)"
    default_integration = {
        "slug": "marki",
        "name": "Marki — defibrylatory",
        "publisher": "Gmina Miasto Marki",
        "source_url": "https://api.dane.gov.pl/media/resources/20250710/Defibrylator_GminaMiastoMarki_1.csv",
        "homepage_url": "https://api.dane.gov.pl/1.4/datasets/4955",
        "attribution": "Gmina Miasto Marki",
        "config": {"bounds": [52.30, 21.04, 52.37, 21.17]},
        "description": "Zewnętrzny CSV opakowuje każdą linię w jedno pole; współrzędne w kolejności lat, lon.",
        **CC_BY,
    }

    def rows(self, raw) -> list[dict]:
        outer = list(csv.reader(io.StringIO(decode(raw))))
        inner_text = "\n".join(row[0] if len(row) == 1 else ",".join(row) for row in outer if row)
        return read_csv(inner_text, delimiter=",")
