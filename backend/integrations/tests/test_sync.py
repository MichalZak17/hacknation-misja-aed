"""The sync engine end to end against Postgres/PostGIS, with each connector's download replaced by a fixture."""

from datetime import date, timedelta

import pytest
from django.core.management import call_command

from devices.models import Device, MaintenanceEvent, MatchCandidate
from integrations.connectors import REGISTRY
from integrations.engine import SyncRefused, execute_run, queue_sync
from integrations.models import Integration, SourceRecord, SyncRun

pytestmark = pytest.mark.django_db


@pytest.fixture
def feeds(monkeypatch):
    """Every URL feed's download replaced by the saved copy in its own fixtures/ folder."""
    for cls in REGISTRY.values():
        if cls.default_integration:
            raw = cls.fixture_path().read_bytes()
            monkeypatch.setattr(cls, "fetch", lambda self, raw=raw: raw)
    call_command("seed_integrations")


def run(slug, kind="historical", **kwargs):
    integration = Integration.objects.get(slug=slug)
    sync_run = SyncRun.objects.create(integration=integration, kind=kind, trigger="manual", **kwargs)
    return execute_run(sync_run.pk)


def test_historical_seed_merges_by_stable_id(feeds):
    osm = run("osm-poland")
    assert osm.status == "success", osm.error
    assert osm.created == 5 and Device.objects.count() == 5

    warsaw = run("warszawa-19115")
    assert warsaw.status == "success", warsaw.error
    # Two Warsaw records are referenced from OSM (ref:api-um-warszawa-pl) and join those devices
    assert warsaw.details["merge"]["linked_by_id"] == 2
    assert Device.objects.count() == 5 + 3
    merged = Device.objects.filter(source_count=2)
    assert merged.count() == 2
    device = merged.first()
    assert device.sources == ["osm-poland", "warszawa-19115"]
    # Warsaw outranks OSM for fields it states
    assert device.field_sources["teryt"]["source"] == "warszawa-19115"

    integration = Integration.objects.get(slug="warszawa-19115")
    assert integration.historical_completed_at and integration.next_run_at


def test_historical_runs_once_unless_forced(feeds):
    run("krosno")
    integration = Integration.objects.get(slug="krosno")
    with pytest.raises(SyncRefused):
        queue_sync(integration, "historical", "manual")
    assert queue_sync(integration, "historical", "manual", force=True).status == "queued"


def test_periodic_diff_unchanged_then_removed(feeds, fixture_bytes, tmp_path, monkeypatch):
    run("krosno")
    again = run("krosno", kind="periodic")
    assert (again.created, again.updated, again.unchanged, again.removed) == (0, 0, 21, 0)

    # The feed drops its last row: that record is marked removed and its device goes inactive
    trimmed = tmp_path / "krosno_trimmed.csv"
    trimmed.write_bytes(b"\n".join(fixture_bytes("krosno.csv").splitlines()[:-1]))
    monkeypatch.setattr(REGISTRY["krosno_csv"], "fetch", lambda self: trimmed.read_bytes())
    removed = run("krosno", kind="periodic")
    assert removed.removed == 1 and removed.unchanged == 20
    assert Device.objects.filter(active=False).count() == 1


def test_dry_run_writes_nothing(feeds):
    result = run("przemysl", dry_run=True)
    assert result.status == "success" and result.created == 21
    assert SourceRecord.objects.count() == 0 and Device.objects.count() == 0
    assert Integration.objects.get(slug="przemysl").historical_completed_at is None


def test_invalid_records_are_stored_but_never_devices(feeds):
    result = run("marki")
    assert result.invalid == 1
    bad = SourceRecord.objects.get(integration__slug="marki", source_record_id="7")
    assert not bad.is_valid and bad.device is None and "outside_municipality" in bad.issues
    assert Device.objects.count() == 7


def test_failure_is_a_failed_run_not_data(feeds, monkeypatch):
    def boom(self):
        from integrations.connectors import ConnectorError

        raise ConnectorError("Download failed: 503")

    monkeypatch.setattr(REGISTRY["krosno_csv"], "fetch", boom)
    result = run("krosno")
    assert result.status == "failed" and "503" in result.error
    assert SourceRecord.objects.count() == 0
    assert Integration.objects.get(slug="krosno").historical_completed_at is None


def test_distance_candidates_between_sources(feeds, settings):
    settings.MATCH_DISTANCE_M = 20_000
    run("krosno")
    marki = run("marki")
    assert marki.status == "success"
    # Marki and Krosno are ~300 km apart: no candidates at 20 km
    assert MatchCandidate.objects.count() == 0
    run("legionowo")
    assert MatchCandidate.objects.count() > 0  # Legionowo is ~14 km from Marki
    assert not MatchCandidate.objects.filter(device_a__sources=["legionowo"], device_b__sources=["legionowo"]).exists()


def test_operator_import_adds_hardware_and_maintenance(feeds, settings, tmp_path):
    run("legionowo")
    target = Device.objects.order_by("id").first()
    soon = date.today() + timedelta(days=10)
    upload = tmp_path / "operator.csv"
    upload.write_text(
        "id,lat,lon,serial_number,manufacturer,pads_replaced_on,pads_expiry_date,battery_expiry_date\n"
        f"OP-1,{target.lat},{target.lon},SN-42,ZOLL,2025-01-10,{soon.isoformat()},2029-01-01\n"
    )
    operator = Integration.objects.create(
        slug="operator-test",
        name="Operator",
        connector="operator_file",
        config={"file_path": str(upload)},
    )
    result = run(operator.slug)
    assert result.status == "success", result.error
    op_device = SourceRecord.objects.get(integration=operator).device
    assert op_device.serial_number == "SN-42"
    assert op_device.readiness == "attention"  # pads expire within 30 days
    assert MaintenanceEvent.objects.filter(device=op_device, kind="pads_replaced", date=date(2025, 1, 10)).exists()
    # Same coordinates as a Legionowo device → a duplicate candidate, not an automatic merge
    assert MatchCandidate.objects.filter(status="pending").exists()


def test_filled_reference_template_imports_and_exports(feeds, tmp_path):
    """schema.xlsx filled in by an operator (Polish headers, one row) uploads as is, and its device comes out of
    aeds.csv with the operator-only columns and the self-test time in UTC."""
    import csv
    import io

    from django.test import Client
    from openpyxl import load_workbook

    from devices.reference_scope import build_reference_xlsx

    workbook = load_workbook(io.BytesIO(build_reference_xlsx()))
    sheet = workbook.worksheets[0]
    sheet.delete_rows(3, 2)
    sheet["A2"] = "SP1-AED-1"
    upload = tmp_path / "dysponent.xlsx"
    workbook.save(upload)
    operator = Integration.objects.create(
        slug="operator-xlsx", name="Operator", connector="operator_file", config={"file_path": str(upload)}
    )
    result = run(operator.slug)
    assert result.status == "success", result.error
    device = SourceRecord.objects.get(integration=operator).device
    assert device.serial_number == "PRZYKLAD-SN-0001" and device.access_conditions == [
        "ask_staff_or_security",
        "only_during_opening_hours",
    ]
    rows = csv.DictReader(io.StringIO(Client().get("/api/export/aeds.csv").content.decode("utf-8-sig")))
    row = next(r for r in rows if r["id"] == device.id)
    assert row["last_self_test_at"] == "2026-11-20T02:00:00Z" and row["operator_regon"] == "123456785"
    assert "access_conditions" not in row  # one true/false column per condition instead of a list
    assert (
        row["access_conditions_ask_staff_or_security"] == row["access_conditions_only_during_opening_hours"] == "true"
    )


def test_dispatch_queues_due_periodic_syncs(feeds, django_capture_on_commit_callbacks):
    from django.utils import timezone

    from integrations.engine import dispatch_due

    run("krosno")
    Integration.objects.filter(slug="krosno").update(next_run_at=timezone.now() - timedelta(minutes=1))
    with django_capture_on_commit_callbacks(execute=True):
        queued = dispatch_due()
    assert len(queued) == 1
    assert SyncRun.objects.get(pk=queued[0]).status == "success"  # eager Celery ran it


@pytest.mark.parametrize(
    ("value", "floor"),
    [("0", "0"), ("+1", "1"), ("-2", "-2"), ("01", "1"), (3, "3"), (2.0, "2"), ("0.5", None), ("0,5", None)]
    + [("0;1", None), ("4_-_klatka_d", None), ("-0.75", None), ("o", None), ("", None), (None, None), (True, None)],
)
def test_floor_is_a_whole_number(value, floor):
    from integrations.connectors.common import to_floor

    assert to_floor(value) == floor


def test_floor_that_is_not_a_number_moves_to_location_detail(feeds, tmp_path, settings):
    """The schema's floor is an integer (the portal types the CSV column as one): a mezzanine or a description stays
    readable in location_detail instead, and records stored before the rule are normalised by the merge."""
    settings.LLM_ENABLED = False  # it would read a floor out of the moved text, which is fine but not under test
    upload = tmp_path / "operator.csv"
    upload.write_text(
        "id,lat,lon,floor,location_detail\n"
        'OP-1,52.1,21.1,"0,5",Hol\n'
        "OP-2,52.2,21.2,+1,\n"
        "OP-3,52.3,21.3,4_-_klatka_d,piętro: 4_-_klatka_d\n"
    )
    operator = Integration.objects.create(
        slug="operator-floors", name="Operator", connector="operator_file", config={"file_path": str(upload)}
    )
    assert run(operator.slug).status == "success"
    devices = {r.source_record_id: r.device for r in SourceRecord.objects.filter(integration=operator)}
    assert (devices["OP-1"].floor, devices["OP-1"].location_detail) == (None, "Hol; piętro: 0,5")
    assert (devices["OP-2"].floor, devices["OP-2"].location_detail) == ("1", None)
    assert (devices["OP-3"].floor, devices["OP-3"].location_detail) == (None, "piętro: 4_-_klatka_d")

    # a record stored before the rule still says "0.5": the merge skips it
    from devices.merge import merge_records

    record = SourceRecord.objects.get(integration=operator, source_record_id="OP-2")
    record.data = record.data | {"floor": "0.5"}
    record.save(update_fields=["data"])
    merge_records([record.pk])
    record.device.refresh_from_db()
    assert record.device.floor is None


def test_jsonld_links_devices_to_their_source_pages(feeds):
    import json

    from devices.exports import build_jsonld

    run("osm-poland")
    run("krosno")
    places = json.loads(build_jsonld("https://aed.example.pl"))["@graph"][1:]
    links = [url for place in places for url in place.get("sameAs", [])]
    # Only OSM declares record_url_template: every OSM device links its object, Krosno's devices link nothing
    assert len(links) == SourceRecord.objects.filter(integration__slug="osm-poland", device__isnull=False).count() > 0
    assert all(url.startswith("https://www.openstreetmap.org/node/") for url in links)
