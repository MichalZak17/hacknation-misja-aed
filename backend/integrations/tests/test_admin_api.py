"""The admin API as the UI uses it: operator integrations are the only ones created here, and for existing ones the
UI edits the source details, the on/off switches and the area. Priority, interval and connector options stay in code."""

import pytest
from django.core.management import call_command

from integrations.models import Integration, SyncRun

pytestmark = pytest.mark.django_db


def post(client, path, body):
    return client.post(path, body, content_type="application/json", headers={"X-CSRFToken": client.token})


def patch(client, path, body):
    return client.patch(path, body, content_type="application/json", headers={"X-CSRFToken": client.token})


@pytest.fixture
def seeded():
    call_command("seed_integrations")


def test_create_operator_source(admin_client):
    response = post(
        admin_client,
        "/api/integrations",
        {"name": " Metro ", "connector": "operator_file", "publisher": "Metro Warszawskie", "attribution": "Metro"},
    )
    assert response.status_code == 200, response.content
    created = response.json()
    assert created["slug"] == "metro" and created["name"] == "Metro"
    assert (created["priority"], created["periodic_enabled"], created["accepts_upload"]) == (90, False, True)
    assert created["attribution"] == "Metro"


@pytest.mark.parametrize("connector", ["mapped", "krosno_csv", "nope"])
def test_fetched_sources_are_not_created_from_the_ui(admin_client, connector):
    response = post(admin_client, "/api/integrations", {"name": "Feed", "connector": connector})
    assert response.status_code == 400 and "kodzie" in response.json()["detail"]
    assert not Integration.objects.filter(slug="feed").exists()


def test_create_operator_rejects_connector_options(admin_client):
    response = post(
        admin_client, "/api/integrations", {"name": "Metro", "connector": "operator_file", "config": {"teryt": "1"}}
    )
    assert response.status_code == 400 and "teryt" in response.json()["detail"]
    ok = post(
        admin_client,
        "/api/integrations",
        {"name": "Metro", "connector": "operator_file", "config": {"bounds": [52.1, 20.8, 52.4, 21.3]}},
    )
    assert ok.status_code == 200 and ok.json()["config"]["bounds"] == [52.1, 20.8, 52.4, 21.3]


def test_patch_details(admin_client, seeded):
    changed = patch(
        admin_client,
        "/api/integrations/krosno",
        {
            "name": "  Krosno — AED  ",
            "description": "Opis",
            "source_url": "https://example.org/v2.csv",
            "homepage_url": "https://api.dane.gov.pl/1.4/datasets/3624",
        },
    )
    assert changed.status_code == 200, changed.content
    body = changed.json()
    assert body["name"] == "Krosno — AED" and body["source_url"] == "https://example.org/v2.csv"


@pytest.mark.parametrize(
    "body, field",
    [
        ({"name": "   "}, "name"),
        ({"source_url": "not a url"}, "source_url"),
        ({"source_url": ""}, "source_url"),
        ({"config": {"bounds": [1, 2]}}, "bounds"),
    ],
)
def test_patch_rejects_bad_values(admin_client, seeded, body, field):
    before = Integration.objects.get(slug="krosno")
    response = patch(admin_client, "/api/integrations/krosno", body)
    assert response.status_code == 400 and field in response.json()["detail"]
    after = Integration.objects.get(slug="krosno")
    assert (after.name, after.source_url, after.config) == (before.name, before.source_url, before.config)


def test_patch_config_changes_only_the_area(admin_client, seeded):
    stored = Integration.objects.get(slug="krosno").config
    # The UI sends the whole config back with new bounds: allowed
    ok = patch(admin_client, "/api/integrations/krosno", {"config": {**stored, "bounds": [49.6, 21.6, 49.8, 21.9]}})
    assert ok.status_code == 200 and ok.json()["config"] == {**stored, "bounds": [49.6, 21.6, 49.8, 21.9]}
    # Leaving bounds out removes the area check and keeps every other option
    cleared = patch(admin_client, "/api/integrations/krosno", {"config": {"teryt": stored["teryt"]}})
    assert cleared.status_code == 200 and cleared.json()["config"] == {"teryt": stored["teryt"]}
    # Any other option belongs in the connector's code
    refused = patch(admin_client, "/api/integrations/krosno", {"config": {"teryt": "0000000"}})
    assert refused.status_code == 400 and "teryt" in refused.json()["detail"]
    assert Integration.objects.get(slug="krosno").config["teryt"] == stored["teryt"]


def test_preview_endpoint_is_gone(admin_client):
    response = post(admin_client, "/api/integrations/preview", {"source_url": "https://example.org", "format": "csv"})
    assert response.status_code in {404, 405}


@pytest.mark.parametrize("body", [{"priority": 1}, {"sync_interval_hours": 1}, {"connector": "mapped"}])
def test_patch_refuses_what_code_declares(admin_client, seeded, body):
    response = patch(admin_client, "/api/integrations/krosno", body)
    assert response.status_code == 422
    krosno = Integration.objects.get(slug="krosno")
    assert (krosno.priority, krosno.sync_interval_hours, krosno.connector) == (50, 24, "krosno_csv")


def test_create_refuses_priority(admin_client):
    response = post(admin_client, "/api/integrations", {"name": "Metro", "connector": "operator_file", "priority": 10})
    assert response.status_code == 422


def test_priority_and_interval_follow_the_connector_class(seeded, monkeypatch):
    from integrations.connectors import REGISTRY

    krosno = Integration.objects.get(slug="krosno")
    # Written around the API (e.g. a shell): save() puts the declared values back
    krosno.priority = 99
    krosno.save()
    assert Integration.objects.get(slug="krosno").priority == 50
    # A redeploy with new declared values: seed_integrations applies them to the existing row
    monkeypatch.setattr(REGISTRY["krosno_csv"], "priority", 55)
    monkeypatch.setattr(REGISTRY["krosno_csv"], "sync_interval_hours", 6)
    Integration.objects.filter(slug="krosno").update(priority=50)  # as stored before the deploy
    call_command("seed_integrations")
    krosno = Integration.objects.get(slug="krosno")
    assert (krosno.priority, krosno.sync_interval_hours) == (55, 6)


def test_list_shows_recent_runs_newest_first_and_running(admin_client, seeded, django_assert_max_num_queries):
    krosno, przemysl = Integration.objects.get(slug="krosno"), Integration.objects.get(slug="przemysl")
    for n in range(14):
        SyncRun.objects.create(integration=krosno, kind="periodic", trigger="schedule", status="success", fetched=n)
    SyncRun.objects.create(integration=przemysl, kind="historical", trigger="manual", status="queued")
    with django_assert_max_num_queries(4):
        listed = {i["slug"]: i for i in admin_client.get("/api/integrations").json()}
    runs = listed["krosno"]["recent_runs"]
    assert len(runs) == 12 and runs[0]["id"] > runs[-1]["id"]
    assert listed["krosno"]["last_run"]["id"] == runs[0]["id"] and not listed["krosno"]["running"]
    assert listed["przemysl"]["running"] and listed["przemysl"]["recent_runs"][0]["status"] == "queued"
    assert listed["marki"]["recent_runs"] == [] and listed["marki"]["last_run"] is None
    priorities = [i["priority"] for i in listed.values()]
    assert priorities == sorted(priorities, reverse=True)


def test_runs_are_paged_without_details(admin_client, seeded):
    krosno = Integration.objects.get(slug="krosno")
    for _ in range(5):
        SyncRun.objects.create(
            integration=krosno,
            kind="periodic",
            trigger="schedule",
            status="success",
            details={"changes": [{"op": "create"}]},
        )
    page = admin_client.get("/api/integrations/krosno/runs?limit=2&offset=2").json()
    assert page["count"] == 5 and len(page["items"]) == 2
    assert page["items"][0]["id"] > page["items"][1]["id"] and page["items"][0]["details"] == {}
    full = admin_client.get(f"/api/runs/{page['items'][0]['id']}").json()
    assert full["details"]["changes"] == [{"op": "create"}]
