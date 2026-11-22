"""LLM extraction from free text, end to end through the sync engine, with the model replaced by a fake."""

import pytest
from django.core.cache import cache
from django.core.management import call_command

from devices.models import Device
from integrations import enrichment, live
from integrations.connectors import REGISTRY
from integrations.connectors.common import is_opening_hours
from integrations.engine import SyncRefused, execute_run, queue_sync
from integrations.models import Integration, SourceRecord, SyncRun, TextExtraction


def fake_answer(text_input: dict) -> dict:
    text = " ".join(str(v) for v in text_input.values()).lower()
    return {
        "placement": "outside_on_building" if "na ścianie" in text else "inside_building",
        "floor": -1 if "poziomie -1" in text else None,
        "opening_hours": None,
        "access_conditions": ["ask_staff_or_security"] if "obsługi pasażerów" in text else [],
        "seasonal": False,
        "device_count": None,
        "enclosure": "unknown",
        "position_hint": "przy bramce nr 5" if "bramce" in text else None,
    }


@pytest.fixture
def llm(settings, monkeypatch):
    settings.LLM_ENABLED = True
    calls = []

    def call_model(client, text_input):
        calls.append(text_input)
        return fake_answer(text_input)

    monkeypatch.setattr(enrichment, "call_model", call_model)
    monkeypatch.setattr(enrichment, "health_problem", lambda: "")
    return calls


@pytest.fixture
def osm(monkeypatch, fixture_bytes):
    monkeypatch.setattr(REGISTRY["openaedmap"], "fetch", lambda self: fixture_bytes("osm_sample.geojson"))
    call_command("seed_integrations")


def device_with(location: str) -> Device:
    return SourceRecord.objects.get(raw__contains={"defibrillator:location": location}).device


def run(kind="historical"):
    integration = Integration.objects.get(slug="osm-poland")
    sync_run = SyncRun.objects.create(integration=integration, kind=kind, trigger="manual")
    return execute_run(sync_run.pk)


def test_clean_output_maps_onto_device_fields_and_drops_out_of_range():
    out = enrichment.clean_output(
        {
            "placement": "vehicle",
            "floor": 400,
            "opening_hours": "Całodobowo",
            "access_conditions": ["siren_or_alarm_button", "siren_or_alarm_button", "bogus"],
            "seasonal": False,
            "device_count": 1,
            "enclosure": "unknown",
            "position_hint": "  ",
        }
    )
    assert out == {"placement": "vehicle", "is_mobile": True, "access_conditions": ["siren_or_alarm_button"]}
    inside = enrichment.clean_output({"placement": "inside_building", "floor": 0, "opening_hours": "24/7"})
    assert inside == {"placement": "inside_building", "indoor": True, "floor": "0", "opening_hours": "24/7"}


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("24/7", True),
        ("Mo-Fr 07:30-15:30; Sa-Su, PH off", True),
        ("Sep-Jun 06:00-21:00; Jul-Aug 07:00-16:00", True),
        ('Mo-Sa 06:00-22:00; Su 08:00-20:00 "tylko niedziele handlowe"', True),
        ("Całodobowo", False),
        ("24h", False),
        ("7-21:30", False),
        ('|| "Brak stałych godzin funkcjonowania."', False),
        ("W godzinach pracy urzędu 7:30 - 15:30", False),
    ],
)
def test_is_opening_hours(value, ok):
    assert is_opening_hours(value) is ok


def test_osm_text_input_and_prose_hours_stay_raw(parse_feed):
    raw = (
        b'{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point",'
        b'"coordinates":[21.0,52.2]},"properties":{"@osm_type":"node","@osm_id":1,"opening_hours":"Ca\\u0142odobowo",'
        b'"indoor":"yes","name":"Urz\\u0105d"}}]}'
    )
    records, integration = parse_feed("openaedmap", raw)
    record = records[0]
    assert "opening_hours" not in record.data and record.data["opening_hours_raw"] == "Całodobowo"
    # No location text, but the prose hours are worth reading; the name is not sent
    assert REGISTRY["openaedmap"](integration).text_input(record) == {"opening_hours": "Całodobowo", "indoor": "yes"}


@pytest.mark.django_db
def test_sync_extracts_once_and_merge_prefers_source_values(llm, osm):
    first = run()
    assert first.status == "success", first.error
    stats = first.details["enrichment"]
    # 4 of the 5 nodes have free text; the fifth has only structured tags and is not sent
    assert stats["records"] == 4 and stats["llm_calls"] == 4 and stats["failed"] == 0 and len(llm) == 4
    assert TextExtraction.objects.count() == 4

    metro = device_with("W punkcie Obsługi Pasażerów Komunikacji Miejskiej na poziomie -1.")
    # The source's level tag wins over the model's floor; inferred-only fields are filled and marked
    assert metro.floor == "-2" and metro.field_sources["floor"].get("method") is None
    assert metro.access_conditions == ["ask_staff_or_security"]
    assert metro.field_sources["access_conditions"]["method"] == "inferred"
    assert metro.placement == "inside_building"

    gate = device_with("Na ścianie budynku przy bramce nr 5")
    assert gate.placement == "outside_on_building" and gate.indoor is False
    assert gate.field_sources["indoor"].get("method") is None  # indoor=no is the source's own tag
    assert SourceRecord.objects.get(device=gate).inferred["position_hint"] == "przy bramce nr 5"

    # Same feed again: nothing changed, nothing is sent
    again = run("periodic")
    assert again.status == "success" and again.unchanged == 5
    assert "enrichment" not in again.details and len(llm) == 4


@pytest.mark.django_db
def test_new_prompt_version_reextracts_from_cache_first(llm, osm, monkeypatch):
    run()
    monkeypatch.setattr(enrichment, "PROMPT_VERSION", "test-v2")
    again = run("periodic")
    assert again.details["enrichment"]["llm_calls"] == 4  # new key, so new calls
    assert again.details["enrichment"]["records_updated"] == 4


@pytest.mark.django_db
def test_model_down_never_fails_the_sync(settings, monkeypatch, osm):
    settings.LLM_ENABLED = True
    monkeypatch.setattr(enrichment, "health_problem", lambda: "model server unreachable")
    result = run()
    assert result.status == "success", result.error
    assert result.details["enrichment"]["problem"] == "model server unreachable"
    assert not SourceRecord.objects.exclude(inferred={}).exists()
    # Keys stay empty, so the next sync tries again
    assert not SourceRecord.objects.exclude(inferred_key="").exists()


@pytest.mark.django_db
def test_disabled_llm_sends_nothing(settings, osm, monkeypatch):
    settings.LLM_ENABLED = False
    monkeypatch.setattr(enrichment, "call_model", lambda *a: pytest.fail("LLM called while disabled"))
    result = run()
    assert result.status == "success" and "enrichment" not in result.details


@pytest.mark.django_db
def test_live_state_reports_phases_answers_and_tallies(llm, osm):
    first = run()
    state = live.read(first.pk)
    assert state["phase"] == "done" and state["status"] == "success"
    assert list(state["phases"]) == ["fetch", "validate", "diff", "classify", "write", "done"]
    assert state["total"] == state["done"] == state["llm_calls"] == 4 and state["failed"] == 0
    assert [e["seq"] for e in state["events"]] == [1, 2, 3, 4]
    assert {e["kind"] for e in state["events"]} == {"ok"}
    assert sum(state["tallies"]["placement"].values()) == 4
    assert state["tallies"]["access_conditions"] == {"ask_staff_or_security": 1}
    metro = next(e for e in state["events"] if "poziomie -1" in e["input"].get("defibrillator:location", ""))
    assert metro["output"]["floor"] == "-1" and "floor" in metro["source_wins"]  # the level tag beats the model
    # The run keeps the answers for when the cache entry is gone
    assert len(first.details["enrichment"]["samples"]) == 4
    assert first.details["enrichment"]["tallies"] == state["tallies"]


@pytest.mark.django_db
def test_reextract_asks_the_model_again_and_rewrites_answers(llm, osm, monkeypatch):
    run()
    assert len(llm) == 4
    monkeypatch.setattr(enrichment, "call_model", lambda client, text: {**fake_answer(text), "seasonal": True})
    integration = Integration.objects.get(slug="osm-poland")
    again = execute_run(queue_sync(integration, "periodic", "manual", reextract=True).pk)
    stats = again.details["enrichment"]
    assert again.status == "success" and again.reextract and again.unchanged == 5
    assert stats["fresh"] and stats["llm_calls"] == 4 and stats["cache_hits"] == 0 and stats["records_updated"] == 4
    assert SourceRecord.objects.filter(inferred__seasonal=True).count() == 4


@pytest.mark.django_db
def test_reextract_cannot_be_a_dry_run(osm):
    with pytest.raises(SyncRefused):
        queue_sync(Integration.objects.get(slug="osm-poland"), "periodic", "manual", dry_run=True, reextract=True)


@pytest.mark.django_db
def test_live_endpoint_pages_with_a_cursor_and_survives_cache_loss(admin_client, llm, osm):
    first = run()
    body = admin_client.get(f"/api/runs/{first.pk}/live?after=2").json()
    assert [e["seq"] for e in body["events"]] == [3, 4]
    assert body["live"]["phase"] == "done" and "events" not in body["live"]
    assert body["summary"]["enrichment"]["llm_calls"] == 4 and "samples" not in body["summary"]["enrichment"]
    assert body["summary"]["merge"] is not None

    cache.delete(live.key(first.pk))
    rebuilt = admin_client.get(f"/api/runs/{first.pk}/live").json()
    assert rebuilt["live"]["phase"] == "done" and len(rebuilt["events"]) == 4
    assert rebuilt["live"]["tallies"]["access_conditions"] == {"ask_staff_or_security": 1}


@pytest.mark.django_db
def test_sync_endpoint_queues_a_reextract(admin_client, llm, osm):
    response = admin_client.post(
        "/api/integrations/osm-poland/sync",
        {"kind": "periodic", "reextract": True},
        content_type="application/json",
        headers={"X-CSRFToken": admin_client.token},
    )
    assert response.status_code == 202 and response.json()["reextract"] is True
    assert SyncRun.objects.get().reextract


@pytest.mark.django_db
def test_enrichment_status_lists_sources_with_text(admin_client, llm, osm):
    run()
    body = admin_client.get("/api/enrichment").json()
    assert body["enabled"] and body["model"] and body["problem"] == ""
    assert body["sources"][0] == {"slug": "osm-poland", "name": body["sources"][0]["name"], "with_text": 4}


@pytest.mark.django_db
def test_live_endpoints_need_an_admin(client, osm):
    assert client.get("/api/enrichment").status_code == 401
    assert client.get("/api/runs/1/live").status_code == 401
