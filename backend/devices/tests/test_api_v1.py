"""/api/v1: the Standard API (annex 3 to Program otwierania danych 2021–2027) over the merged dataset."""

from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.management import call_command
from django.test import Client

from devices.cache import bump_data_version
from devices.models import Device
from integrations.connectors import REGISTRY
from integrations.engine import execute_run
from integrations.models import Integration, SyncRun

pytestmark = pytest.mark.django_db

ERROR_KEYS = {"error-result", "error-reason", "error-code", "error-help", "status"}


@pytest.fixture
def seeded(monkeypatch, fixture_bytes, settings):
    settings.PUBLIC_BASE_URL = "https://aed.example"
    settings.EXTRA_PUBLIC_BASE_URLS = []
    monkeypatch.setattr(REGISTRY["krosno_csv"], "fetch", lambda self: fixture_bytes("krosno.csv"))
    call_command("seed_integrations")
    integration = Integration.objects.get(slug="krosno")
    execute_run(SyncRun.objects.create(integration=integration, kind="historical", trigger="seed").pk)


@pytest.fixture
def client():
    return Client()


def assert_error(response, status: int, code: int):
    assert response.status_code == status, response.content
    assert response["Content-Type"].startswith("application/json")
    errors = response.json()["errors"]
    assert len(errors) == 1 and set(errors[0]) >= ERROR_KEYS
    assert errors[0]["error-code"] == code and errors[0]["status"] == str(status)
    assert errors[0]["error-help"] == f"https://aed.example/api/v1/errors/{code}"
    return errors[0]


def query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def test_collection_document_and_pagination_links(seeded, client):
    response = client.get("/api/v1/aeds?limit=5&page=2&filter[source]=krosno")
    assert response.status_code == 200 and response["Content-Type"].startswith("application/json")
    assert "Content-Disposition" not in response
    body = response.json()
    assert body["jsonapi"] == {"version": "1.0"}
    assert body["meta"]["count"] == 21 and body["meta"]["pages"] == 5 and body["meta"]["page"] == 2
    assert body["meta"]["api-version"] == "1.0.0" and "data-version" in body["meta"] and "date-mod" in body["meta"]
    assert len(body["data"]) == 5
    item = body["data"][0]
    assert item["type"] == "aeds" and "id" not in item["attributes"]
    assert item["links"]["self"] == f"https://aed.example/api/v1/aeds/{item['id']}"
    assert {"lat", "lon", "access", "readiness", "sources", "municipality", "updated_at"} <= set(item["attributes"])
    links = body["links"]
    assert all(
        links[k].startswith("https://aed.example/api/v1/aeds?") for k in ("self", "first", "prev", "next", "last")
    )
    assert query(links["self"]) == {"filter[source]": "krosno", "page": "2", "limit": "5"}
    assert query(links["first"])["page"] == "1" and query(links["prev"])["page"] == "1"
    assert query(links["next"])["page"] == "3" and query(links["last"])["page"] == "5"
    # Following the links walks the whole collection once, in id order
    ids, url = [], links["first"]
    while url:
        page = client.get(url.removeprefix("https://aed.example")).json()
        ids += [d["id"] for d in page["data"]]
        url = page["links"]["next"]
    assert len(ids) == 21 == len(set(ids)) and ids == sorted(ids)


def test_first_and_last_page_links_and_jsonapi_spellings(seeded, client):
    first = client.get("/api/v1/aeds?page[size]=10").json()
    assert first["links"]["prev"] is None and first["meta"]["limit"] == 10
    last = client.get("/api/v1/aeds?page[number]=3&page[size]=10").json()
    assert last["links"]["next"] is None and len(last["data"]) == 1
    beyond = client.get("/api/v1/aeds?page=9&limit=10").json()
    assert beyond["data"] == [] and query(beyond["links"]["prev"])["page"] == "3"


def test_filters(seeded, client):
    devices = Device.objects.filter(active=True)
    sample = devices.exclude(teryt__isnull=True).first()
    if sample is None:  # PRG boundaries not loaded in the test database: give one device a code
        sample = devices.first()
        Device.objects.filter(pk=sample.pk).update(teryt="1807011", city="Krosno")
        bump_data_version()
        sample.refresh_from_db()
    by_voivodeship = client.get(f"/api/v1/aeds?filter[teryt]={sample.teryt[:2]}").json()
    assert by_voivodeship["meta"]["count"] == devices.filter(teryt__startswith=sample.teryt[:2]).count() >= 1
    assert all(d["attributes"]["teryt"].startswith(sample.teryt[:2]) for d in by_voivodeship["data"])
    city = client.get(f"/api/v1/aeds?filter[city]={sample.city.upper()}").json()
    assert city["meta"]["count"] == devices.filter(city__iexact=sample.city).count()
    access = client.get("/api/v1/aeds?filter[access]=public,limited,private,unknown").json()
    assert access["meta"]["count"] == 21
    assert client.get("/api/v1/aeds?filter[readiness]=ready").json()["meta"]["count"] == 0
    assert client.get("/api/v1/aeds?filter[operational_status]=unknown,operational").json()["meta"]["count"] == 21
    assert client.get("/api/v1/aeds?filter[source]=krosno").json()["meta"]["count"] == 21
    assert client.get("/api/v1/aeds?filter[updated_since]=2000-01-01").json()["meta"]["count"] == 21
    assert client.get("/api/v1/aeds?filter[updated_since]=2999-01-01T00:00:00Z").json()["meta"]["count"] == 0
    bbox = client.get("/api/v1/aeds?filter[bbox]=21.70,49.70,21.73,49.73").json()["meta"]["count"]
    assert 0 < bbox < 21


def test_sort_and_sparse_fieldsets(seeded, client):
    body = client.get("/api/v1/aeds?sort=-lat,id&fields=lat,city&limit=100").json()
    lats = [d["attributes"]["lat"] for d in body["data"]]
    assert lats == sorted(lats, reverse=True)
    assert all(set(d["attributes"]) == {"lat", "city"} for d in body["data"])
    jsonapi = client.get("/api/v1/aeds?fields[aeds]=lon&limit=1").json()
    assert set(jsonapi["data"][0]["attributes"]) == {"lon"}


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("/api/v1/aeds?foo=1", 40001),
        ("/api/v1/aeds?fields[devices]=lat", 40001),
        ("/api/v1/aeds?filter[colour]=red", 40002),
        ("/api/v1/aeds?filter[access]=everyone", 40003),
        ("/api/v1/aeds?filter[teryt]=123", 40003),
        ("/api/v1/aeds?filter[source]=nope", 40003),
        ("/api/v1/aeds?filter[updated_since]=yesterday", 40003),
        ("/api/v1/aeds?filter[bbox]=1,2,3", 40003),
        ("/api/v1/aeds?filter[city]=", 40003),
        ("/api/v1/aeds?sort=-colour", 40004),
        ("/api/v1/aeds?fields=lat,colour", 40005),
        ("/api/v1/aeds?limit=501", 40006),
        ("/api/v1/aeds?page=0", 40006),
        ("/api/v1/aeds?page=abc", 40006),
        ("/api/v1/version?x=1", 40001),
    ],
)
def test_bad_requests(seeded, client, url, code):
    error = assert_error(client.get(url), 400, code)
    assert error["error-reason"] and error.get("error-solution")


def test_single_aed_404_410_301(seeded, client):
    device = Device.objects.filter(active=True).order_by("id").first()
    body = client.get(f"/api/v1/aeds/{device.pk}?fields=lat").json()
    assert body["data"]["id"] == device.pk and body["data"]["attributes"] == {"lat": device.lat}
    assert body["links"]["self"] == f"https://aed.example/api/v1/aeds/{device.pk}?fields=lat"
    assert_error(client.get("/api/v1/aeds/AED-PL-NOPE"), 404, 40402)
    other = Device.objects.filter(active=True).order_by("id")[1]
    Device.objects.filter(pk=device.pk).update(merged_into=other)
    bump_data_version()
    redirect = client.get(f"/api/v1/aeds/{device.pk}")
    assert redirect.status_code == 301 and redirect["Location"] == f"https://aed.example/api/v1/aeds/{other.pk}"
    Device.objects.filter(pk=other.pk).update(active=False)
    bump_data_version()
    assert_error(client.get(f"/api/v1/aeds/{other.pk}"), 410, 41001)


def test_unknown_path_method_and_error_help(seeded, client):
    assert_error(client.get("/api/v1/devices"), 404, 40401)
    error = assert_error(client.get("/api/v1/aeds/"), 404, 40401)
    assert "ukośnik" in error["error-reason"]
    response = client.post("/api/v1/aeds")
    assert_error(response, 405, 40501)
    assert "GET" in response["Allow"]
    assert_error(client.delete("/api/v1"), 405, 40501)
    help_ = client.get("/api/v1/errors/40501").json()
    assert help_["data"]["attributes"]["status"] == 405
    assert any(e["id"] == "40001" for e in client.get("/api/v1/errors").json()["data"])
    assert_error(client.get("/api/v1/errors/1"), 404, 40403)


def test_head_etag_and_cache_invalidation(seeded, client):
    for url in ("/api/v1/aeds", "/api/v1/sources", "/api/v1/version", "/api/v1"):
        get, head = client.get(url), client.head(url)
        assert get.status_code == head.status_code == 200, url
        assert head.content == b"" and head["ETag"] == get["ETag"]
    first = client.get("/api/v1/aeds?limit=2")
    assert client.get("/api/v1/aeds?limit=2", headers={"If-None-Match": first["ETag"]}).status_code == 304
    Device.objects.filter(pk=first.json()["data"][0]["id"]).update(active=False)
    bump_data_version()
    after = client.get("/api/v1/aeds?limit=2", headers={"If-None-Match": first["ETag"]})
    assert after.status_code == 200 and after.json()["meta"]["count"] == 20


def test_sources_version_index_and_docs(seeded, client):
    sources = client.get("/api/v1/sources").json()
    krosno = next(s for s in sources["data"] if s["id"] == "krosno")
    assert krosno["type"] == "sources" and krosno["attributes"]["records"] == 21
    assert krosno["links"]["aeds"] == "https://aed.example/api/v1/aeds?filter[source]=krosno"
    version = client.get("/api/v1/version").json()["api-version"]
    assert version["major"] == "1" and {"minor", "patch", "date-mod"} <= set(version)
    index = client.get("/api/v1").json()
    assert index["links"]["aeds"] == "https://aed.example/api/v1/aeds" and index["meta"]["limits"] == "none"
    spec = client.get("/api/v1/openapi.json").json()
    assert spec["openapi"].startswith("3.") and "/api/v1/aeds" in spec["paths"]
    names = {p["name"] for p in spec["paths"]["/api/v1/aeds"]["get"]["parameters"]}
    assert {"filter[teryt]", "sort", "fields", "page", "limit"} <= names
    assert client.get("/api/v1/docs").status_code == 200
    # The unversioned API the frontend uses is unchanged
    assert set(client.get("/api/devices?limit=1").json()) == {"count", "items"}


def test_semantic_context_in_the_link_header(seeded):
    response = Client().get("/api/v1/aeds?limit=1")
    assert 'rel="http://www.w3.org/ns/json-ld#context"' in response["Link"]
    assert "/api/v1/context>" in response["Link"]
    ctx = Client().get("/api/v1/context").json()["@context"]
    assert ctx["lat"] == "https://schema.org/latitude" and ctx["@vocab"].endswith("/api/schema#")
