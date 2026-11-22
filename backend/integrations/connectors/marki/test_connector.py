"""Marki connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""

from integrations.engine import validate


def test_marki_unwraps_swaps_and_rejects_foreign_point(fixture_bytes, parse_feed):
    records, integration = parse_feed("marki_csv", fixture_bytes("marki.csv"))
    assert len(records) == 8
    validated = validate(records, integration)
    by_id = {r.source_record_id: (r, valid) for r, valid in validated}
    first, valid = by_id["1"]
    assert valid and "coordinates_swapped" in first.issues
    assert round(first.lat, 3) == 52.327 and round(first.lon, 3) == 21.108
    # Row 7 carries Krosno's coordinates: inside Poland, outside Marki
    seventh, valid = by_id["7"]
    assert not valid and "outside_municipality" in seventh.issues
