"""Legionowo connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""


def test_legionowo_derived_ids_are_stable(fixture_bytes, parse_feed):
    raw = fixture_bytes("legionowo.csv")
    first, _ = parse_feed("legionowo_csv", raw)
    second, _ = parse_feed("legionowo_csv", raw)
    assert len(first) == 24
    assert [r.source_record_id for r in first] == [r.source_record_id for r in second]
    assert first[0].data["simc"] == "0920806"
    assert first[0].data["address"].startswith("ul. Piłsudskiego")
