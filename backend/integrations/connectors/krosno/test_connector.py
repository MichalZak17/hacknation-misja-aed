"""Krosno connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""

from integrations.engine import validate


def test_krosno_header_whitespace(fixture_bytes, parse_feed):
    records, integration = parse_feed("krosno_csv", fixture_bytes("krosno.csv"))
    assert len(records) == 21
    assert records[0].source_record_id == "1"
    assert records[0].data["postal_code"] == "38-400"
    assert records[0].data["city"] == "Krosno"
    assert all(valid for _, valid in validate(records, integration))
