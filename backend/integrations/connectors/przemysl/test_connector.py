"""Przemyśl connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""

from integrations.engine import validate


def test_przemysl(fixture_bytes, parse_feed):
    records, integration = parse_feed("przemysl_geojson", fixture_bytes("przemysl.geojson"))
    assert len(records) == 21
    assert all(valid for _, valid in validate(records, integration))
    assert any(r.data.get("photo_url") for r in records)
