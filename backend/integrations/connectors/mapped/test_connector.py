"""The mapped connector, with a config written in code: Krosno's CSV mapped column by column."""

import pytest

from integrations.connectors.mapped.connector import MappedConnector, validate_config
from integrations.engine import execute_run
from integrations.models import Integration, SyncRun

KROSNO_CONFIG = {
    "format": "csv",
    "id": "Numer Id",
    "lat": "Szerokość geograficzna",
    "lon": "Długość geograficzna",
    "fields": {"building_name": "Lokalizacja", "address": "Adres"},
    "constants": {"teryt": "1861011"},
    "bounds": [49.64, 21.66, 49.75, 21.85],
}


def test_validate_config():
    assert validate_config(KROSNO_CONFIG) == []
    errors = validate_config({"format": "xml", "fields": {"not_a_field": "x"}, "bounds": [50, 20, 49, 21]})
    assert any(e.startswith("format") for e in errors)
    assert any(e.startswith("id") for e in errors)
    assert any("not_a_field" in e for e in errors)
    assert any(e.startswith("bounds") for e in errors)
    # Coordinates are only required from columns when the format has no geometry
    assert validate_config({"format": "geojson", "id": "id"}) == []
    assert any(e.startswith("lat") for e in validate_config({"format": "csv", "id": "id"}))


@pytest.mark.django_db
def test_mapped_feed_syncs(monkeypatch, fixture_bytes):
    monkeypatch.setattr(MappedConnector, "fetch", lambda self: fixture_bytes("krosno.csv"))
    integration = Integration.objects.create(
        slug="krosno-mapped", name="Krosno", connector="mapped", config=KROSNO_CONFIG
    )
    run = execute_run(SyncRun.objects.create(integration=integration, kind="historical", trigger="manual").pk)
    assert run.status == "success", run.error
    assert run.created == 21 and run.invalid == 0
    record = integration.records.get(source_record_id="2")
    assert record.data["building_name"] == "Kampus Sportowo-dydaktyczny, portiernia"
    assert record.data["teryt"] == "1861011"


@pytest.mark.django_db
def test_broken_config_fails_the_run_readably(monkeypatch, fixture_bytes):
    monkeypatch.setattr(MappedConnector, "fetch", lambda self: fixture_bytes("krosno.csv"))
    integration = Integration.objects.create(slug="broken", name="Broken", connector="mapped", config={"format": "xml"})
    run = execute_run(SyncRun.objects.create(integration=integration, kind="historical", trigger="manual").pk)
    assert run.status == "failed" and "Invalid mapped config" in run.error
    assert not integration.records.exists()
