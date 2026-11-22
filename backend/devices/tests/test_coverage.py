import pytest
from django.test import Client
from django.utils import timezone

from devices.coverage import coverage, is_filled
from devices.models import Device
from devices.schema import SCHEMA
from integrations.models import Integration, SourceRecord

pytestmark = pytest.mark.django_db


def record(integration, n, data, **extra):
    return SourceRecord.objects.create(
        integration=integration, source_record_id=str(n), lat=52.0, lon=21.0, data=data, content_hash=str(n), **extra
    )


@pytest.fixture
def sources():
    city = Integration.objects.create(slug="city", name="Miasto", connector="none", priority=60)
    osm = Integration.objects.create(slug="osm", name="OSM", connector="none", priority=10)
    Integration.objects.create(slug="off", name="Wyłączone", connector="none", enabled=False)
    record(city, 1, {"address": "ul. Prosta 5", "access": "public", "indoor": False, "access_conditions": []})
    record(city, 2, {"address": "Kościelna", "access": "unknown", "city": "  "})
    record(osm, 1, {"access": "public", "opening_hours": "24/7"})
    record(osm, 2, {"access": "private", "access_conditions": ["key_holder"]})
    # Removed or invalid records do not count
    record(osm, 3, {"opening_hours": "24/7"}, removed_at=timezone.now())
    record(osm, 4, {"opening_hours": "24/7"}, is_valid=False)
    seen = {"seen": "2026-11-20"}
    Device.objects.create(
        id="AED-PL-000001",
        lat=52.0,
        lon=21.0,
        address="ul. Prosta 5",
        access="public",
        teryt="1465011",
        is_mobile=False,
        sources=["city", "osm"],
        field_sources={
            "lat": {"source": "city", **seen},
            "address": {"source": "city", **seen},
            "access": {"source": "city", **seen},
            "teryt": {"source": "prg", "method": "geocoded", **seen},
        },
    )
    Device.objects.create(
        id="AED-PL-000002",
        lat=52.1,
        lon=21.1,
        access="private",
        opening_hours="24/7",
        is_mobile=False,
        sources=["osm"],
        field_sources={
            "lat": {"source": "osm", **seen},
            "access": {"source": "osm", **seen},
            "opening_hours": {"source": "osm", "method": "inferred", **seen},
        },
    )
    # Inactive and merged-away devices are not part of the dataset
    Device.objects.create(id="AED-PL-000003", lat=52.2, lon=21.2, access="public", active=False)


def test_is_filled():
    assert not any(is_filled(v) for v in (None, "", "  ", "unknown", [], {}))
    assert all(is_filled(v) for v in ("x", 0, False, ["a"], 1.5))


def test_coverage_per_source_and_merged(sources):
    result = coverage()
    assert [s["slug"] for s in result["sources"]] == ["city", "osm"]  # enabled only, by priority
    assert {s["slug"]: s["records"] for s in result["sources"]} == {"city": 2, "osm": 2}
    assert result["merged"] == {"records": 2}
    assert [f["field"] for f in result["fields"]] == [f.field for f in SCHEMA]
    assert [lv["level"] for lv in result["levels"]] == [1, 2, 3]

    fields = {f["field"]: f for f in result["fields"]}
    assert fields["access"]["sources"]["city"] == {"count": 1, "pct": 50.0}  # "unknown" is not filled
    assert fields["access"]["sources"]["osm"] == {"count": 2, "pct": 100.0}
    assert fields["city"]["sources"]["city"]["count"] == 0  # blank string
    assert fields["indoor"]["sources"]["city"]["count"] == 1  # False is a stated value
    assert fields["access_conditions"]["sources"]["city"]["count"] == 0
    assert fields["access_conditions"]["sources"]["osm"]["count"] == 1
    assert fields["opening_hours"]["sources"]["osm"] == {"count": 1, "pct": 50.0}
    assert fields["lat"]["sources"]["osm"]["count"] == 2
    # Address parts come from the address: "Kościelna" has a street but no prefix or number
    assert fields["street"]["sources"]["city"]["count"] == 2
    assert fields["street_type"]["sources"]["city"]["count"] == 1
    assert fields["house_number"]["sources"]["city"]["count"] == 1
    # Fields only the merge sets do not apply to a source
    assert fields["id"]["sources"]["city"] is None and fields["readiness"]["sources"]["osm"] is None

    merged = {name: f["merged"] for name, f in fields.items()}
    assert merged["access"]["count"] == 2 and merged["access"]["pct"] == 100.0
    assert {(b["source"], b["count"]) for b in merged["access"]["by_source"]} == {("city", 1), ("osm", 1)}
    assert merged["teryt"]["by_source"] == [{"source": "prg", "method": "geocoded", "count": 1}]
    assert merged["opening_hours"]["by_source"] == [{"source": "osm", "method": "inferred", "count": 1}]
    assert merged["house_number"]["count"] == 1 and merged["house_number"]["by_source"][0]["source"] == "city"
    assert merged["lon"]["by_source"] == merged["lat"]["by_source"]
    assert merged["readiness"]["count"] == 0  # "unknown"
    assert merged["is_mobile"]["count"] == 0  # the default False, stated by no source
    assert merged["id"]["count"] == 2


def test_coverage_endpoint_is_public_and_cached(sources):
    client = Client()
    first = client.get("/api/sources/coverage")
    assert first.status_code == 200
    body = first.json()
    assert body["merged"]["records"] == 2 and len(body["fields"]) == len(SCHEMA)
    Device.objects.filter(pk="AED-PL-000002").update(active=False)
    assert client.get("/api/sources/coverage").json()["merged"]["records"] == 2  # same data version
