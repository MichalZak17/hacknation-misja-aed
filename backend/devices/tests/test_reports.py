import json

import pytest
from django.test import Client

from devices.models import Device, DeviceReport

pytestmark = pytest.mark.django_db

VALID = {"kind": "not_working", "description": "Lampka miga na czerwono, brak elektrod w szafce."}


def post(client, body, ip="203.0.113.7"):
    return client.post("/api/reports", json.dumps(body), content_type="application/json", REMOTE_ADDR=ip)


@pytest.fixture
def device():
    return Device.objects.create(id="AED-PL-000123", lat=52.23, lon=21.01, building_name="Dworzec Centralny")


def test_public_report_is_stored_without_raw_ip(device):
    # No session and no CSRF token: the public form posts as anyone
    client = Client(enforce_csrf_checks=True)
    response = post(
        client,
        {**VALID, "device_id": " aed-pl-000123 ", "lat": 52.2301, "lon": 21.0102, "contact_email": "jan@example.pl"},
    )
    assert response.status_code == 201 and response.json() == {"received": True}
    report = DeviceReport.objects.get()
    assert report.device_id == "AED-PL-000123" and report.status == "new"
    assert report.contact_email == "jan@example.pl" and report.lat == 52.2301
    assert len(report.ip_hash) == 64 and "203.0.113.7" not in report.ip_hash


def test_report_follows_a_merged_device(device):
    Device.objects.create(id="AED-PL-000999", lat=52.23, lon=21.01, merged_into=device)
    assert post(Client(), {**VALID, "device_id": "AED-PL-000999"}).status_code == 201
    assert DeviceReport.objects.get().device_id == "AED-PL-000123"


@pytest.mark.parametrize(
    "body, field",
    [
        ({"kind": "spam", "description": "x"}, "kind"),
        ({"kind": "locked", "description": "   "}, "description"),
        ({"kind": "locked", "description": "x" * 2001}, "description"),
        ({**VALID, "contact_email": "nie-email"}, "contact_email"),
        ({**VALID, "lat": 52.2}, "location"),
        ({**VALID, "lat": 48.1, "lon": 11.5}, "location"),  # Munich
        ({**VALID, "device_id": "AED-PL-404"}, "device_id"),
    ],
)
def test_invalid_reports_name_the_field(body, field):
    response = post(Client(), body)
    assert response.status_code == 400
    assert field in response.json()["errors"]
    assert not DeviceReport.objects.exists()


def test_honeypot_looks_fine_but_stores_nothing():
    response = post(Client(), {**VALID, "website": "http://spam.example"})
    assert response.status_code == 201 and response.json() == {"received": True}
    assert not DeviceReport.objects.exists()


def test_rate_limit_per_sender():
    client = Client()
    assert [post(client, VALID).status_code for _ in range(6)] == [201] * 5 + [429]
    # Another sender is not affected; the first proxy hop counts, not the proxy itself
    assert post(client, VALID, ip="198.51.100.1").status_code == 201
    forwarded = client.post(
        "/api/reports",
        json.dumps(VALID),
        content_type="application/json",
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_FORWARDED_FOR="192.0.2.50, 10.0.0.1",
    )
    assert forwarded.status_code == 201
    assert DeviceReport.objects.count() == 7


def test_admin_endpoints_need_a_session():
    client = Client()
    assert client.get("/api/reports").status_code == 401
    assert client.patch("/api/reports/1", "{}", content_type="application/json").status_code == 401
    assert client.delete("/api/reports/1").status_code == 401


def test_admin_inbox(admin_client, device):
    post(Client(), {**VALID, "device_id": device.id})
    post(
        Client(), {"kind": "missing_aed", "description": "AED w bibliotece", "lat": 50.06, "lon": 19.94}, ip="192.0.2.9"
    )
    headers = {"X-CSRFToken": admin_client.token}

    inbox = admin_client.get("/api/reports?status=new").json()
    assert inbox["count"] == 2 and inbox["counts"]["new"] == 2
    item = next(i for i in inbox["items"] if i["device"])
    assert item["device"]["name"] == "Dworzec Centralny" and item["kind_label"] == "AED nie działa / brak elektrod"
    assert "ip_hash" not in item

    updated = admin_client.patch(
        f"/api/reports/{item['id']}",
        json.dumps({"status": "resolved", "admin_note": "Dysponent wymienił elektrody."}),
        content_type="application/json",
        headers=headers,
    )
    assert updated.status_code == 200 and updated.json()["status"] == "resolved"
    after = admin_client.get("/api/reports?status=new").json()
    assert after["count"] == 1 and after["counts"] == {"new": 1, "in_review": 0, "resolved": 1, "rejected": 0}

    bad = admin_client.patch(
        f"/api/reports/{item['id']}", json.dumps({"status": "done"}), content_type="application/json", headers=headers
    )
    assert bad.status_code == 422

    assert admin_client.delete(f"/api/reports/{item['id']}", headers=headers).status_code == 204
    assert DeviceReport.objects.count() == 1


def test_reports_stay_out_of_the_dataset(device):
    post(Client(), {**VALID, "device_id": device.id, "description": "Tajny opis zgłoszenia 7f3a"})
    for path in ("/api/export/aeds.json", "/api/export/aeds.csv", f"/api/devices/{device.id}"):
        assert "7f3a" not in Client().get(path).content.decode()
