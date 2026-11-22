"""Municipality and town from coordinates (devices/boundaries.py), through the merge, on made-up boundaries."""

import json

import pytest
from django.db import connection
from django.test import Client

from devices import boundaries
from devices.merge import merge_records
from devices.models import Device
from integrations.models import Integration, SourceRecord

pytestmark = pytest.mark.django_db


def square(west, south, east, north):
    return json.dumps(
        {
            "type": "Polygon",
            "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        }
    )


@pytest.fixture
def units():
    """A town (_4) and the rural rest (_5) of one urban-rural municipality, side by side at lon 20.01, and a rural
    municipality (_2) east of it at lon 20.03."""
    rows = [
        ("999901_4", "Testowo - miasto", square(20.00, 50.00, 20.01, 50.01)),
        ("999901_5", "Testowo - obszar wiejski", square(20.01, 50.00, 20.03, 50.01)),
        ("999902_2", "Wsiowo - gmina wiejska", square(20.03, 50.00, 20.05, 50.01)),
    ]
    with connection.cursor() as cursor:
        boundaries.insert_units(
            cursor,
            [
                {
                    "code": code,
                    "name": name,
                    **boundaries.unit_values(code, name),
                    "version": "2026-05-06",
                    "geojson": g,
                }
                for code, name, g in rows
            ],
            srid=4326,
        )


def merged(points: dict[str, tuple[float, float, dict]]) -> dict[str, Device]:
    integration = Integration.objects.create(slug="test-src", name="Test", connector="openaedmap")
    records = [
        SourceRecord.objects.create(
            integration=integration, source_record_id=key, lat=lat, lon=lon, data=data, content_hash=key
        )
        for key, (lat, lon, data) in points.items()
    ]
    merge_records([r.pk for r in records])
    return {r.source_record_id: Device.objects.get(records=r) for r in records}


def test_unit_values():
    assert boundaries.unit_values("121501_1", "Jordanów - gmina miejska") == {
        "teryt": "1215011",
        "city": "Jordanów",
        "municipality": "gmina miejska Jordanów",
    }
    assert boundaries.unit_values("121508_2", "Zawoja - gmina wiejska")["city"] is None
    assert boundaries.unit_values("121506_4", "Maków Podhalański - miasto")["teryt"] == "1215063"
    assert boundaries.unit_values("121506_4", "Maków Podhalański - miasto")["city"] == "Maków Podhalański"
    assert boundaries.unit_values("121506_5", "Maków Podhalański - obszar wiejski")["city"] is None
    assert boundaries.unit_values("146519_8", "Żoliborz - dzielnica")["teryt"] == "1465011"
    assert boundaries.unit_values("126103_9", "Kraków-Nowa Huta") == {
        "teryt": "1261011",
        "city": "Kraków",
        "municipality": "gmina miejska Kraków",
    }


def test_merge_fills_only_what_the_boundaries_make_certain(units):
    devices = merged(
        {
            "town": (50.005, 20.005, {}),
            "next-to-town": (50.005, 20.0101, {}),  # ~7 m outside the town: same municipality, town unsure
            "rural": (50.005, 20.02, {}),
            "next-to-other-municipality": (50.005, 20.0301, {}),  # ~7 m from another municipality: nothing
            "source-says": (50.005, 20.005, {"city": "Testowo Dolne"}),
            "abroad": (49.0, 20.0, {}),
        }
    )
    town = devices["town"]
    assert (town.teryt, town.city) == ("9999013", "Testowo")
    assert town.field_sources["city"] == {"source": "prg", "seen": "2026-05-06", "method": "geocoded"}
    assert town.address is None and town.postal_code is None  # never derived from coordinates
    assert (devices["next-to-town"].teryt, devices["next-to-town"].city) == ("9999013", None)
    assert (devices["rural"].teryt, devices["rural"].city) == ("9999013", None)
    assert "city" not in devices["rural"].field_sources
    assert (devices["next-to-other-municipality"].teryt, devices["next-to-other-municipality"].city) == (None, None)
    says = devices["source-says"]
    assert says.city == "Testowo Dolne" and says.field_sources["city"]["source"] == "test-src"
    assert says.teryt == "9999013"
    assert (devices["abroad"].teryt, devices["abroad"].city) == (None, None)

    body = Client().get(f"/api/devices/{devices['rural'].pk}").json()
    assert body["municipality"] == "gmina miejsko-wiejska Testowo"


def test_merge_without_boundaries_leaves_fields_empty():
    device = merged({"a": (50.005, 20.005, {})})["a"]
    assert device.teryt is None and device.city is None and "teryt" not in device.field_sources


def test_coverage_by_region(units):
    devices = merged({"town": (50.005, 20.005, {}), "rural": (50.005, 20.02, {}), "abroad": (49.0, 20.0, {})})
    Device.objects.filter(pk=devices["town"].pk).update(access="public", opening_hours="24/7")
    client = Client()

    municipalities = client.get("/api/stats/regions?level=municipality").json()
    assert municipalities["unlocated"] == 1  # abroad
    rows = {r["teryt"]: r for r in municipalities["items"]}
    testowo, wsiowo = rows["9999013"], rows["9999022"]
    assert testowo["name"] == "gmina miejsko-wiejska Testowo" and testowo["devices"] == 2
    assert testowo["by_access"]["public"] == 1 and testowo["public_24_7"] == 1 and testowo["open_24_7"] == 1
    assert 2.2 < testowo["area_km2"] < 2.6 and testowo["per_100_km2"] == round(2 / testowo["area_km2"] * 100, 2)
    assert wsiowo["devices"] == 0 and wsiowo["per_100_km2"] == 0  # a municipality with no AED is listed

    voivodeships = client.get("/api/stats/regions").json()
    assert voivodeships["level"] == "voivodeship" and voivodeships["items"][0]["teryt"] == "99"
    assert voivodeships["items"][0]["devices"] == 2

    assert client.get("/api/stats/regions?level=county").status_code == 400
    assert client.get("/api/stats/regions?voivodeship=99").status_code == 400
    assert client.get("/api/stats/regions?level=municipality&voivodeship=12").json()["items"] == []
