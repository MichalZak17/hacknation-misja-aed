"""OpenAEDMap connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""


def test_osm_keys_tags_and_warsaw_refs(fixture_bytes, parse_feed):
    records, _ = parse_feed("openaedmap", fixture_bytes("osm_sample.geojson"))
    assert len(records) == 5
    assert all(r.source_record_id.startswith("node/") for r in records)
    assert {r.refs.get("warszawa-19115") for r in records[:2]} == {"1150", "925"}
    assert all(r.data.get("verified_on") for r in records[2:])  # check_date → verified_on
    assert all(49 < r.lat < 55 and 14 < r.lon < 25 for r in records)
