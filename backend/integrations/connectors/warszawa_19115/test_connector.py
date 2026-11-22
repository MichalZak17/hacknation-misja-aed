"""Warsaw 19115 connector against a saved copy of its real feed (fixtures/, fetched 21.11.2026)."""


def test_warsaw(fixture_bytes, parse_feed):
    records, _ = parse_feed("warsaw_arcgis", fixture_bytes("warsaw_sample.geojson"))
    assert len(records) == 5
    first = records[0]
    assert first.data["teryt"] == "1465011"
    assert first.data["access"] in {"public", "private"}
    assert 52 < first.lat < 53


def test_street_prefix_from_the_city_address_register():
    from integrations.connectors.warszawa_19115.connector import full_street, street_type

    assert street_type("Suwalska") == "ul."
    assert street_type("K. Szajnochy") == "ul."  # initials: matched by the unambiguous last word
    assert street_type("al. Krakowska") is None  # the feed already wrote the prefix
    assert street_type("Nieistniejąca Ulica Testowa XYZ") is None  # never guessed
    assert full_street("Suwalska") == "ul. Suwalska"
    assert full_street(None) is None
