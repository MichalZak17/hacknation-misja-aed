import csv
import gzip
import io
import json
from datetime import date, timedelta

import pytest
from django.core.management import call_command
from django.test import Client

from devices.cache import bump_data_version
from devices.models import Device
from devices.readiness import compute_readiness
from integrations.connectors import REGISTRY
from integrations.engine import execute_run
from integrations.models import Integration, SyncRun

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(monkeypatch, fixture_bytes):
    monkeypatch.setattr(REGISTRY["krosno_csv"], "fetch", lambda self: fixture_bytes("krosno.csv"))
    call_command("seed_integrations")
    integration = Integration.objects.get(slug="krosno")
    execute_run(SyncRun.objects.create(integration=integration, kind="historical", trigger="seed").pk)


def test_public_endpoints(seeded):
    client = Client()
    stats = client.get("/api/stats").json()
    assert stats["active_devices"] == 21 and stats["by_readiness"]["unknown"] == 21
    completeness = stats["completeness"]
    assert set(completeness) == {
        "address",
        "location_detail",
        "access_known",
        "opening_hours",
        "maintenance",
        "verified",
        "operator",
        "photo",
    }
    assert sum(stats["by_placement"].values()) == 21 and sum(stats["by_source_count"].values()) == 21
    assert sum(stats["verification_age"].values()) == 21
    assert all(0 <= n <= 21 for n in completeness.values()) and completeness["maintenance"] == 0
    listing = client.get("/api/devices?q=OSP&limit=5").json()
    assert listing["count"] >= 2
    nearest = client.get("/api/devices/nearest?lat=49.69&lon=21.77&limit=3").json()
    assert len(nearest) == 3 and nearest[0]["distance_m"] <= nearest[1]["distance_m"]
    points = client.get("/api/devices/points").json()
    assert len(points["features"]) == 21
    detail = client.get(f"/api/devices/{nearest[0]['id']}").json()
    assert detail["records"][0]["integration"] == "krosno" and detail["serial_number"] is None
    bbox = client.get("/api/devices?bbox=21.70,49.70,21.73,49.73").json()
    assert 0 < bbox["count"] < 21


def test_exports_and_etag(seeded):
    client = Client()
    csv_response = client.get("/api/export/aeds.csv")
    assert csv_response.status_code == 200 and csv_response.content.decode("utf-8-sig").startswith("id,lat,lon,")
    geojson = client.get("/api/export/aeds.geojson")
    assert len(geojson.json()["features"]) == 21
    assert client.get("/api/export/aeds.geojson", headers={"If-None-Match": geojson["ETag"]}).status_code == 304
    assert client.get("/api/export/schema.xlsx").content[:2] == b"PK"


def test_points_served_as_cached_bytes_with_etag(seeded):
    client = Client()
    plain = client.get("/api/devices/points")
    assert plain.status_code == 200 and "Content-Encoding" not in plain and plain["Cache-Control"] == "no-cache"
    zipped = client.get("/api/devices/points", headers={"Accept-Encoding": "gzip, br"})
    assert zipped["Content-Encoding"] == "gzip" and zipped["ETag"] != plain["ETag"]
    assert json.loads(gzip.decompress(zipped.content)) == plain.json()
    revalidate = {"Accept-Encoding": "gzip", "If-None-Match": f"W/{zipped['ETag']}"}
    assert client.get("/api/devices/points", headers=revalidate).status_code == 304
    # A sync, merge or event bumps the data version: the old ETag no longer matches
    Device.objects.filter(pk=plain.json()["features"][0]["properties"]["id"]).update(active=False)
    bump_data_version()
    fresh = client.get("/api/devices/points", headers=revalidate)
    assert fresh.status_code == 200 and len(json.loads(gzip.decompress(fresh.content))["features"]) == 20


def test_csv_spells_booleans_like_the_schema(seeded):
    first, second = Device.objects.filter(active=True).order_by("id")[:2]
    Device.objects.filter(pk=first.pk).update(indoor=True, is_mobile=False, pediatric_mode=None)
    Device.objects.filter(pk=second.pk).update(pediatric_mode=True)
    bump_data_version()
    text = Client().get("/api/export/aeds.csv").content.decode("utf-8-sig")
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["id"] == first.id
    assert (row["indoor"], row["is_mobile"], row["pediatric_mode"]) == ("true", "false", ".")  # . = no data
    assert "True" not in text and "False" not in text


def test_csv_has_no_empty_columns_and_utc_datetimes(seeded):
    """Standard techniczny §4: no completely empty column. A column appears once any record fills it, in schema
    order; datetimes are UTC with a Z (the portal's datetime check rejects a +01:00 offset)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from devices.exports import csv_columns
    from devices.schema import PUBLISHED_FIELDS

    def columns():
        text = Client().get("/api/export/aeds.csv").content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return reader.fieldnames, list(reader)

    header, rows = columns()
    assert header == [f for f in csv_columns() if f in header]  # schema order
    assert all(any(r[column] not in ("", ".") for r in rows) for column in header)
    assert "serial_number" not in header and "last_self_test_at" not in header
    # one elementary value per cell: no one-line address, no list columns, no empty cells
    assert "address" not in header and "sources" not in header and "access_conditions" not in header
    assert all(value != "" for r in rows for value in r.values())

    device = Device.objects.filter(active=True).order_by("id").first()
    tested = datetime(2026, 11, 20, 3, 0, tzinfo=ZoneInfo("Europe/Warsaw"))
    Device.objects.filter(pk=device.pk).update(
        serial_number="SN-1", last_self_test_at=tested, access_conditions=["key_holder"]
    )
    bump_data_version()
    header, rows = columns()
    assert header == [f for f in csv_columns() if f in header]
    assert rows[0]["serial_number"] == "SN-1" and rows[0]["last_self_test_at"] == "2026-11-20T02:00:00Z"
    assert rows[1]["serial_number"] == "." and rows[1]["last_self_test_at"] == "."
    assert rows[0]["access_conditions_key_holder"] == "true" and rows[0]["access_conditions_staff_only"] == "false"
    assert rows[1]["access_conditions_key_holder"] == "."
    # GeoJSON and JSON keep every published field, lists as lists
    assert Client().get("/api/export/aeds.json").json()["fields"] == PUBLISHED_FIELDS
    # the record sources, one pair per row
    pairs = list(csv.DictReader(io.StringIO(Client().get("/api/export/aeds-sources.csv").content.decode("utf-8-sig"))))
    assert pairs and set(pairs[0]) == {"aed_id", "source", "source_record_id", "source_record_url"}
    assert {p["aed_id"] for p in pairs} == {r["id"] for r in rows}


def test_csv_passes_the_portal_tabular_checks(seeded):
    """What dane.gov.pl's type guesser and table validation need: coordinates with 6 decimals (7 make a 10-character
    value it takes for a date), floor as a whole number, and the special sign "." instead of an empty cell in every
    column it types (dates, numbers, booleans, numeric codes), declared on the resource."""
    import re

    first, second = Device.objects.filter(active=True).order_by("id")[:2]
    Device.objects.filter(pk=first.pk).update(lat=49.58789561, lon=21.7, floor="0.5", verified_on=None, indoor=True)
    Device.objects.filter(pk=second.pk).update(floor="2", verified_on=date(2026, 1, 1), address=None)
    bump_data_version()
    text = Client().get("/api/export/aeds.csv").content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    row = rows[0]
    assert (row["lat"], row["lon"]) == ("49.587896", "21.700000")
    assert all(re.fullmatch(r"-?\d+\.\d{6}", r[c]) for r in rows for c in ("lat", "lon"))
    assert row["floor"] == "." and row["verified_on"] == "."
    assert all(r["floor"] == "." or re.fullmatch(r"-?\d+", r["floor"]) for r in rows)
    assert all(r["indoor"] in {"true", "false", "."} for r in rows)
    assert all(r["teryt"] == "." or re.fullmatch(r"\d{7}", r["teryt"]) for r in rows)
    assert any(r["street"] == "." for r in rows)  # no empty cells: free text without data holds the special sign too
    # the other formats agree on the floor
    item = next(i for i in Client().get("/api/export/aeds.json").json()["items"] if i["id"] == first.id)
    assert item["floor"] is None


def test_json_exports_have_one_record_per_line(seeded, settings):
    """A one-line 20 MB JSON hangs dane.gov.pl (libmagic says text/plain, rdflib's N-Triples parser is quadratic in
    the line length). Same documents, one item, feature or node per line."""
    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    client = Client()
    for path, key in (("aeds.json", "items"), ("aeds.geojson", "features"), ("aeds.jsonld", "@graph")):
        content = client.get(f"/api/export/{path}").content
        body = json.loads(content)
        lines = content.decode().splitlines()
        assert len(lines) == len(body[key]) + 2, path
        assert all(json.loads(line.rstrip(",")) for line in lines[1:-1])
    assert len(json.loads(client.get("/api/export/aeds.json").content)["items"]) == 21


def test_reference_scope_files(seeded):
    """schema.xlsx: the template first (Polish headers, example rows, codes as text), then the dictionary, the
    allowed values and instructions; the same template as CSV next to it."""
    from openpyxl import load_workbook

    from devices.reference_scope import EXAMPLE_ROWS, template_columns, template_header

    client = Client()
    response = client.get("/api/export/schema.xlsx")
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Wzorcowy zakres danych", "Słownik pól", "Dozwolone wartości", "Instrukcja"]
    template = workbook.worksheets[0]
    rows = list(template.iter_rows(values_only=True))
    assert list(rows[0]) == template_header() and len(rows) == 1 + len(EXAMPLE_ROWS)
    assert "Adres" not in rows[0] and "Warunki dostępu" not in rows[0]  # one elementary value per cell
    teryt = [c.name for c in template_columns()].index("teryt") + 1
    assert template.cell(row=3, column=teryt).value == "0264011"  # leading zero kept: a text cell
    assert template.cell(row=3, column=teryt).number_format == "@" and template.freeze_panes == "B2"
    assert template.data_validations.dataValidation  # dropdowns for the enumerations
    dictionary = list(workbook["Słownik pól"].iter_rows(values_only=True))
    assert len(dictionary) == 1 + len(template_columns())
    key_holder = next(r for r in dictionary if r[1] == "access_conditions_key_holder")
    assert key_holder[3] == "logiczny" and key_holder[8] == "false"
    access = next(r for r in dictionary if r[1] == "access")
    assert access[6] == "tak" and "public — dostępne dla każdego" in access[7]

    template_csv = client.get("/api/export/schema-template.csv")
    assert template_csv["Content-Type"] == "text/csv; charset=utf-8"
    assert template_csv["Content-Disposition"] == 'attachment; filename="wzorcowy-zakres-danych-aed.csv"'
    assert template_csv.content.startswith(b"\xef\xbb\xbf") and b"\r\n" in template_csv.content
    parsed = list(csv.reader(io.StringIO(template_csv.content.decode("utf-8-sig"))))
    assert parsed[0] == template_header() and len(parsed) == 1 + len(EXAMPLE_ROWS)
    assert parsed[2][teryt - 1] == "0264011"
    assert client.head("/api/export/schema-template.csv").status_code == 200
    assert (
        client.get("/api/export/schema-template.csv", headers={"If-None-Match": template_csv["ETag"]}).status_code
        == 304
    )


def test_write_reference_scope(tmp_path):
    from devices.reference_scope import build_template_csv

    call_command("write_reference_scope", str(tmp_path))
    assert (tmp_path / "wzorcowy-zakres-danych-aed.xlsx").read_bytes()[:2] == b"PK"
    assert (tmp_path / "wzorcowy-zakres-danych-aed.csv").read_bytes() == build_template_csv()


def test_dataset_metadata(seeded, settings):
    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    body = Client().get("/api/export/dataset.json").json()
    assert body["dataset"]["title"] and {c["code"] for c in body["dataset"]["categories"]} == {"HEAL", "REGI"}
    assert body["dataset"]["license_condition_custom_description"]
    assert body["dataset"]["update_frequency"] == "daily" and body["dataset"]["has_high_value_data"] is False
    assert body["dataset"]["license_chosen"] == body["dataset"]["license_name"] == "CC BY-SA 4.0"
    assert body["dataset"]["url"] == "https://aed.example.pl/export"
    assert [r["format"] for r in body["resources"]] == ["csv", "csv", "geojson", "json", "jsonld", "json", "xlsx"]
    assert body["resources"][1]["link"] == "https://aed.example.pl/api/export/aeds-sources.csv"
    api_resource = body["resources"][5]
    assert api_resource["media_type"] == "api" and api_resource["availability"] == "remote"
    assert api_resource["link"] == "https://aed.example.pl/api/v1/aeds"
    csv_resource = body["resources"][0]
    assert csv_resource["is_auto_data_date"] and csv_resource["data_date_update_period"] == "daily"
    assert csv_resource["link"] == "https://aed.example.pl/api/export/aeds.csv"
    assert csv_resource["openness_score"] == 3 and csv_resource["file_size"] > 0
    assert csv_resource["special_signs"] == body["resources"][1]["special_signs"] == ["."]
    assert body["resources"][2]["special_signs"] == []
    # the size and ETag describe the file actually served at that link
    served = Client().get(csv_resource["path"])
    assert len(served.content) == csv_resource["file_size"] and served["ETag"] == f'"{csv_resource["etag"]}"'
    # the portal takes supplements only as doc/docx/pdf/txt/odt
    assert [s["format"] for s in body["supplements"]] == ["txt", "txt"]
    assert body["resources"][6]["openness_score"] == 2
    notes = Client().get("/api/export/notes.txt").content.decode()
    assert "CC BY-SA 4.0" in notes and "https://aed.example.pl/api/sources" in notes
    assert "id — Identyfikator AED" in Client().get("/api/export/schema.txt").content.decode()
    assert body["metadata"]["harvester_url"] == "https://aed.example.pl/api/export/harvester.xml"
    assert body["metadata"]["records"] == 21
    assert any(s["slug"] == "krosno" for s in body["sources"])


def test_harvester_xml(seeded, settings):
    """What the dane.gov.pl harvester checks before its XSD validation: an XML Content-Type, the MD5 at the same URL
    with .md5, a versioned namespace on the root with unqualified children, and https:// resource links."""
    import hashlib
    import xml.etree.ElementTree as ET

    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    client = Client()
    # the harvester sends HEAD first and needs a 2xx with the XML Content-Type
    head = client.head("/api/export/harvester.xml")
    assert head.status_code == 200 and head["Content-Type"].startswith("application/xml")
    assert head.content == b"" and int(head["Content-Length"]) > 0  # gunicorn would otherwise send the body
    assert client.head("/api/export/harvester.md5").status_code == 200
    assert client.head("/api/export/aeds.csv").status_code == 200
    response = client.get("/api/export/harvester.xml")
    assert response["Content-Type"].startswith("application/xml") and "Content-Disposition" not in response
    md5 = client.get("/api/export/harvester.md5").content.decode().strip()
    assert md5 == hashlib.md5(response.content).hexdigest()  # noqa: S324

    root = ET.fromstring(response.content)
    assert root.tag == "{urn:otwarte-dane:harvester:1.13}datasets"
    dataset, dga = root.findall("dataset")
    assert dataset.findtext("extIdent") == "misja-aed-polska" and dataset.findtext("updateFrequency") == "daily"
    assert [c.text for c in dataset.find("categories")] == ["HEAL", "REGI"]
    assert len(dataset.findtext("description/polish")) <= 1000
    assert "https://aed.example.pl/api/sources" in dataset.findtext("description/polish")
    resources = dataset.findall("resources/resource")
    assert [r.findtext("extIdent") for r in resources] == [
        "misja-aed-polska-csv",
        "misja-aed-polska-sources-csv",
        "misja-aed-polska-geojson",
        "misja-aed-polska-json",
        "misja-aed-polska-jsonld",
        "misja-aed-polska-api",
        "misja-aed-polska-xlsx",
    ]
    assert resources[5].findtext("availability") == "remote"
    assert all(r.findtext("url").startswith("https://") for r in resources)
    assert resources[0].findtext("isAutoDataDate") == "true" and resources[0].findtext("autoDataDateStart")
    assert dataset.findtext("supplements/supplement/url") == "https://aed.example.pl/api/export/schema.txt"
    assert dataset.findtext("conditions/dbOrCopyrightedLicenseChosen") == "CC BY-SA 4.0"
    assert [s.text for s in resources[0].findall("specialSigns/specialSign")] == ["."]
    assert all(r.find("specialSigns") is None for r in resources[2:])
    assert "OpenStreetMap" in dataset.findtext("conditions/dbOrCopyrighted")

    # our list of protected data, a dataset of its own: the portal accepts one containsProtectedData resource per
    # XML, only with every other flag false, and copies its rows into the nationwide DGA table every night
    assert dga.findtext("extIdent") == "misja-aed-dga" and [c.text for c in dga.find("categories")] == ["GOVE"]
    assert len(dga.findtext("description/polish")) <= 1000
    flagged = [r for r in root.iter("resource") if r.findtext("containsProtectedData") == "true"]
    assert flagged == dga.findall("resources/resource")
    (protected,) = flagged
    assert protected.findtext("extIdent") == "misja-aed-dga-xlsx" and protected.findtext("availability") == "local"
    url = protected.findtext("url")  # this day's version once archived, like the AED files
    assert url.startswith("https://aed.example.pl/api/export/") and url.endswith("/wykaz-chronionych-danych.xlsx")
    for flag in ("hasDynamicData", "hasHighValueData", "hasHighValueDataFromEuropeanCommissionList", "hasResearchData"):
        assert protected.findtext(flag) == "false" and dga.findtext(flag) == "false"
    assert protected.find("regions") is None and protected.find("specialSigns") is None

    # no licence: the portal rejects dbOrCopyrighted without dbOrCopyrightedLicenseChosen, so both go
    settings.DATASET_LICENSE = ""
    bump_data_version()
    dataset = ET.fromstring(client.get("/api/export/harvester.xml").content).find("dataset")
    assert dataset.find("conditions/dbOrCopyrighted") is None


def test_jsonld_is_linked_data(seeded, settings):
    import json

    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    response = Client().get("/api/export/aeds.jsonld")
    assert response["Content-Type"] == "application/ld+json" and "attachment" in response["Content-Disposition"]
    body = json.loads(response.content)
    assert body["@context"]["@vocab"] == "https://schema.org/"
    dataset, *places = body["@graph"]
    assert dataset["@type"] == "Dataset" and dataset["license"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert len(places) == 21
    assert places[0]["@id"].startswith("https://aed.example.pl/api/devices/AED-PL-")
    assert {"latitude", "longitude"} <= places[0]["geo"].keys()


def test_export_links_follow_an_extra_public_origin(seeded, settings):
    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    settings.EXTRA_PUBLIC_BASE_URLS = ["https://test.example.org"]
    client = Client()
    via_proxy = client.get("/api/export/dataset.json", HTTP_X_FORWARDED_HOST="test.example.org, aed.example.pl").json()
    assert via_proxy["resources"][0]["link"] == "https://test.example.org/api/export/aeds.csv"
    default = client.get("/api/export/dataset.json").json()
    assert default["resources"][0]["link"] == "https://aed.example.pl/api/export/aeds.csv"


@pytest.mark.parametrize(
    ("address", "parts"),
    [
        ("ul. Marszałkowska 126/134", ("ul.", "Marszałkowska", "126/134")),
        ("Aleje Jerozolimskie 54", ("al.", "Jerozolimskie", "54")),
        ("plac Defilad 1", ("pl.", "Defilad", "1")),
        ("Rynek 1", ("rynek", "Rynek", "1")),
        ("Nowy Świat 47A", (None, "Nowy Świat", "47A")),
        ("Pułku 11 Listopada 5 a", (None, "Pułku 11 Listopada", "5a")),
        ("Armii Krajowej", (None, "Armii Krajowej", None)),
        (None, (None, None, None)),
    ],
)
def test_split_address(address, parts):
    from devices.address import split_address

    assert split_address(address) == parts


def test_csv_has_the_address_in_parts(seeded):
    rows = list(csv.DictReader(io.StringIO(Client().get("/api/export/aeds.csv").content.decode("utf-8-sig"))))
    with_address = [r for r in rows if r["street"] != "."]
    assert with_address and "address" not in rows[0]
    assert any(r["house_number"] != "." for r in with_address)


def test_dataset_links_fall_back_to_the_request_host(seeded, settings):
    settings.PUBLIC_BASE_URL = ""
    body = Client().get("/api/export/dataset.json", HTTP_HOST="localhost").json()
    assert body["resources"][0]["link"] == "http://localhost/api/export/aeds.csv"


def test_admin_requires_login(seeded):
    assert Client().get("/api/integrations").status_code == 401


def test_admin_flow(seeded, admin_client):
    integrations = admin_client.get("/api/integrations").json()
    krosno = next(i for i in integrations if i["slug"] == "krosno")
    assert krosno["records"] == 21 and krosno["historical_completed_at"]

    headers = {"X-CSRFToken": admin_client.token}
    refused = admin_client.post(
        "/api/integrations/krosno/sync", {"kind": "historical"}, content_type="application/json", headers=headers
    )
    assert refused.status_code == 409

    patched = admin_client.patch(
        "/api/integrations/krosno", {"periodic_enabled": False}, content_type="application/json", headers=headers
    ).json()
    assert patched["periodic_enabled"] is False and patched["next_run_at"] is None

    device_id = Device.objects.order_by("id").first().id
    event = admin_client.post(
        f"/api/devices/{device_id}/events",
        {"kind": "pads_replaced", "date": "2026-01-01", "next_due": (date.today() + timedelta(days=400)).isoformat()},
        content_type="application/json",
        headers=headers,
    )
    assert event.status_code == 200
    device = Device.objects.get(pk=device_id)
    assert device.pads_replaced_on == date(2026, 1, 1) and device.readiness == "ready"


def test_csrf_enforced_for_admin_writes(seeded, admin_client):
    response = admin_client.patch("/api/integrations/krosno", {"enabled": False}, content_type="application/json")
    assert response.status_code == 403


def test_readiness_rules():
    today = date(2026, 11, 21)
    device = Device(id="x", lat=0, lon=0)
    assert compute_readiness(device, today) == "unknown"
    device.pads_expiry_date = today + timedelta(days=200)
    assert compute_readiness(device, today) == "ready"
    device.battery_expiry_date = today + timedelta(days=5)
    assert compute_readiness(device, today) == "attention"
    device.pads_expiry_date = today - timedelta(days=1)
    assert compute_readiness(device, today) == "expired"
    device.pads_expiry_date, device.operational_status = today + timedelta(days=200), "out_of_service"
    assert compute_readiness(device, today) == "expired"


def test_nearest_aed(seeded):
    client = Client()
    body = client.get("/api/aed/nearest?lat=49.69&lon=21.77").json()
    listed = client.get("/api/devices/nearest?lat=49.69&lon=21.77&limit=1").json()[0]
    assert body["demo"] is False and body["aed"]["id"] == listed["id"]
    assert body["distance_m"] == listed["distance_m"] and body["query"] == {"lat": 49.69, "lon": 21.77}
    assert {"street", "house_number", "opening_hours", "readiness", "municipality"} <= set(body["aed"])
    assert body["links"]["self"].endswith(f"/api/devices/{listed['id']}")
    assert "travelmode=walking" in body["links"]["directions"]

    # devices a rescuer cannot count on are skipped
    Device.objects.filter(pk=listed["id"]).update(operational_status="out_of_service")
    assert client.get("/api/aed/nearest?lat=49.69&lon=21.77").json()["aed"]["id"] != listed["id"]

    assert client.get("/api/aed/nearest?lat=52.23&lon=21.01&max_distance_m=1000").status_code == 404
    assert client.get("/api/aed/nearest?lat=49.69&lon=21.77&access=nope").status_code == 400
    assert client.get("/api/aed/nearest?lat=91&lon=21.77").status_code == 422
    assert client.get("/api/aed/nearest?lon=21.77").status_code == 422


def test_nearby_aeds(seeded):
    client = Client()
    body = client.get("/api/aed/nearby?lat=49.69&lon=21.77&limit=3").json()
    items = body["items"]
    assert body["query"] == {"lat": 49.69, "lon": 21.77} and len(items) == 3
    assert [i["distance_m"] for i in items] == sorted(i["distance_m"] for i in items)
    nearest = client.get("/api/aed/nearest?lat=49.69&lon=21.77").json()
    assert items[0]["aed"]["id"] == nearest["aed"]["id"] and items[0]["distance_m"] == nearest["distance_m"]
    assert {"opening_hours", "access_conditions", "location_detail", "floor", "readiness"} <= set(items[0]["aed"])
    assert "travelmode=walking" in items[0]["links"]["directions"]

    # same skipping rules as /aed/nearest
    Device.objects.filter(pk=items[0]["aed"]["id"]).update(operational_status="missing")
    again = client.get("/api/aed/nearby?lat=49.69&lon=21.77&limit=3").json()["items"]
    assert items[0]["aed"]["id"] not in {i["aed"]["id"] for i in again}

    assert client.get("/api/aed/nearby?lat=52.23&lon=21.01&max_distance_m=1000").json()["items"] == []
    assert client.get("/api/aed/nearby?lat=49.69&lon=21.77&access=nope").status_code == 400
    assert client.get("/api/aed/nearby?lat=49.69&lon=21.77&limit=99").status_code == 422
    assert client.get("/api/aed/nearby?lat=91&lon=21.77").status_code == 422


def test_nearest_aed_demo(db):
    body = Client().get("/api/aed/nearest?lat=52.2297&lon=21.0122&demo=true").json()
    aed = body["aed"]
    assert body["demo"] is True and aed["id"] == "AED-PL-DEMO" and body["links"]["self"] is None
    assert all(value not in (None, "", []) for value in aed.values()), [k for k, v in aed.items() if v in (None, "")]
    assert aed["street"] == "Marszałkowska" and aed["access_conditions"] == ["ask_staff_or_security", "key_holder"]
    assert 0 < body["distance_m"] < 1000
    assert not Device.objects.filter(pk="AED-PL-DEMO").exists()


def test_availability_and_open_now(seeded):
    client = Client()
    first, second = client.get("/api/aed/nearby?lat=49.69&lon=21.77&limit=2").json()["items"]
    Device.objects.filter(pk=first["aed"]["id"]).update(opening_hours="Mo-Fr 08:00-16:00; Sa-Su off")
    Device.objects.filter(pk=second["aed"]["id"]).update(opening_hours="24/7")
    bump_data_version()

    monday = "/api/aed/nearby?lat=49.69&lon=21.77&limit=2&at=2026-11-23T10:00"
    items = client.get(monday).json()["items"]
    assert items[0]["availability"]["state"] == "open"
    assert items[0]["availability"]["until"] == "2026-11-23T16:00:00+01:00"
    assert items[1]["availability"]["open_24_7"] is True

    # Saturday: the office-hours AED is closed, so open_now skips it; AEDs with no hours are never "open"
    saturday = "lat=49.69&lon=21.77&at=2026-11-21T10:00&open_now=true"
    open_items = client.get(f"/api/aed/nearby?{saturday}&limit=5").json()["items"]
    assert [i["aed"]["id"] for i in open_items] == [second["aed"]["id"]]
    assert client.get(f"/api/aed/nearest?{saturday}").json()["aed"]["id"] == second["aed"]["id"]
    nearest = client.get("/api/aed/nearest?lat=49.69&lon=21.77&at=2026-11-21T10:00").json()
    assert nearest["aed"]["id"] == first["aed"]["id"] and nearest["availability"]["state"] == "closed"
    assert nearest["availability"]["next_open"] == "2026-11-23T08:00:00+01:00"

    Device.objects.filter(pk=second["aed"]["id"]).update(opening_hours=None)
    assert client.get(f"/api/aed/nearest?{saturday}").status_code == 404


def test_aed_record(seeded):
    client = Client()
    device_id = client.get("/api/devices?limit=1").json()["items"][0]["id"]
    body = client.get(f"/api/aed/{device_id}").json()
    assert body["demo"] is False and body["aed"]["id"] == device_id and "municipality" in body["aed"]
    assert body["availability"]["state"] in {"open", "closed", "unknown"}
    assert body["links"]["record"].endswith(f"/api/aed/{device_id}")
    assert "origin=" not in body["links"]["directions"] and "destination=" in body["links"]["directions"]

    demo = client.get("/api/aed/AED-PL-DEMO").json()
    assert demo["demo"] is True and demo["aed"]["street"] == "Marszałkowska"
    assert client.get("/api/aed/AED-PL-999999").status_code == 404

    other = Device.objects.filter(active=True).exclude(pk=device_id).first()
    Device.objects.filter(pk=other.pk).update(merged_into_id=device_id, active=False)
    redirect = client.get(f"/api/aed/{other.pk}")
    assert redirect.status_code == 301 and redirect["Location"] == f"/api/aed/{device_id}"
    Device.objects.filter(pk=device_id).update(active=False)
    assert client.get(f"/api/aed/{device_id}").status_code == 410


def test_device_filters(seeded):
    client = Client()
    ids = [d["id"] for d in client.get("/api/devices?limit=3").json()["items"]]
    Device.objects.filter(pk=ids[0]).update(teryt="9901011", opening_hours="24/7", placement="inside_building")
    Device.objects.filter(pk=ids[1]).update(teryt="9902011")
    bump_data_version()

    def found(query):
        return [d["id"] for d in client.get(f"/api/devices?{query}").json()["items"]]

    assert found("teryt=9901011") == [ids[0]]
    assert sorted(found("teryt=99")) == sorted(ids[:2])
    assert found("open_24_7=true") == [ids[0]] and ids[0] not in found("open_24_7=false&limit=500")
    assert found("placement=inside_building") == [ids[0]]
    assert len(found("city=KROSNO&limit=500")) == Device.objects.filter(city__iexact="krosno").count() > 0
    assert client.get("/api/devices?teryt=18x").status_code == 400
    assert client.get("/api/devices?placement=roof").status_code == 400
    assert client.get("/api/devices?access=everyone").status_code == 400

    from django.utils import timezone

    later = timezone.now()
    Device.objects.get(pk=ids[2]).save()  # updated_at moves
    bump_data_version()
    assert found(f"updated_since={later.isoformat().replace('+', '%2B')}") == [ids[2]]


def test_changes_feed(seeded):
    from django.utils import timezone

    client = Client()
    start = timezone.now().isoformat().replace("+", "%2B")
    assert client.get(f"/api/changes?since={start}").json()["count"] == 0

    keep, gone, merged = Device.objects.filter(active=True).order_by("id")[:3]
    keep.building_name = "Nowa nazwa"
    keep.save()
    gone.active = False
    gone.save()
    merged.merged_into, merged.active = keep, False
    merged.save()

    body = client.get(f"/api/changes?since={start}").json()
    by_id = {i["id"]: i for i in body["items"]}
    assert body["count"] == 3 and set(by_id) == {keep.pk, gone.pk, merged.pk}
    assert by_id[keep.pk]["change"] == "updated" and by_id[keep.pk]["aed"]["building_name"] == "Nowa nazwa"
    assert by_id[gone.pk] | {"updated_at": None} == {
        "id": gone.pk,
        "change": "removed",
        "merged_into": None,
        "updated_at": None,
        "aed": None,
    }
    assert by_id[merged.pk]["change"] == "merged" and by_id[merged.pk]["merged_into"] == keep.pk
    as_of = body["as_of"].replace("+", "%2B")
    assert client.get(f"/api/changes?since={as_of}").json()["count"] == 0
    assert len(client.get(f"/api/changes?since={start}&limit=1&offset=1").json()["items"]) == 1
    assert client.get("/api/changes").status_code == 422


def test_daily_versions_get_their_own_addresses(seeded, settings):
    """Standard techniczny: version resources instead of overwriting them (each new file at a new URL, old ones kept).
    The stable URL serves the newest data; the harvester registers the dated one."""
    import xml.etree.ElementTree as ET

    from devices.exports import rebuild_all

    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    rebuild_all()
    versions = Client().get("/api/export/archiwum").json()["versions"]
    assert len(versions) == 1
    day = versions[0]["data_date"]
    assert versions[0]["files"]["aeds.csv"] == f"https://aed.example.pl/api/export/archiwum/{day}/aeds.csv"

    served = Client().get(f"/api/export/archiwum/{day}/aeds.csv")
    assert served.status_code == 200 and served["Content-Disposition"].startswith("attachment")
    assert b"".join(served.streaming_content) == Client().get("/api/export/aeds.csv").content
    assert Client().get(f"/api/export/archiwum/{day}/../../settings.py").status_code == 404
    assert Client().get("/api/export/archiwum/2000-01-01/aeds.csv").status_code == 404

    csv_resource = Client().get("/api/export/dataset.json").json()["resources"][0]
    assert csv_resource["link"] == "https://aed.example.pl/api/export/aeds.csv"
    assert csv_resource["version_link"] == f"https://aed.example.pl/api/export/archiwum/{day}/aeds.csv"
    root = ET.fromstring(Client().get("/api/export/harvester.xml").content)
    urls = [r.findtext("url") for r in root.find("dataset").findall("resources/resource")]
    assert urls[0] == csv_resource["version_link"]
    assert "https://aed.example.pl/api/v1/aeds" in urls  # the API is live, not a version
    dga_url = root.findall("dataset")[1].findtext("resources/resource/url")
    assert dga_url == f"https://aed.example.pl/api/export/archiwum/{day}/wykaz-chronionych-danych.xlsx"
    served = Client().get(f"/api/export/archiwum/{day}/wykaz-chronionych-danych.xlsx")
    assert served["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
