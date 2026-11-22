"""The list of protected data (DGA) as dane.gov.pl checks it before copying it into its nationwide table."""

import io
from mimetypes import guess_extension

import pytest
from django.test import Client
from openpyxl import load_workbook

from devices.cache import bump_data_version
from devices.dga import DGA_COLUMNS, protected_data_rows
from devices.models import DeviceReport
from integrations.models import Integration, SourceRecord

pytestmark = pytest.mark.django_db

# mcod/resources/dga_constants.py: DGA_COLUMNS and the columns whose empty cells drop a row
PORTAL_COLUMNS = [
    "Lp.",
    "Zasób chronionych danych",
    "Format danych",
    "Rozmiar danych",
    "Warunki ponownego wykorzystywania",
]
REQUIRED = ["Zasób chronionych danych", "Format danych", "Rozmiar danych"]


def _sheet(content: bytes):
    return load_workbook(io.BytesIO(content)).worksheets[0]


def test_file_passes_the_portal_checks():
    response = Client().get("/api/export/wykaz-chronionych-danych.xlsx")
    assert response.status_code == 200
    # the portal tells the format by mimetypes.guess_extension(Content-Type): parameters would make it None
    assert guess_extension(response["Content-Type"]) == ".xlsx"
    rows = list(_sheet(response.content).iter_rows(values_only=True))
    assert DGA_COLUMNS == PORTAL_COLUMNS and list(rows[0]) == PORTAL_COLUMNS
    assert len(rows) >= 3  # the reports and the source archive are always listed
    for row in rows[1:]:
        cells = dict(zip(PORTAL_COLUMNS, row, strict=True))
        assert all(str(cells[column] or "").strip() for column in REQUIRED)
    assert [row[0] for row in rows[1:]] == list(range(1, len(rows)))


def test_rows_follow_the_database():
    assert protected_data_rows()[0]["Rozmiar danych"] == "0 zgłoszeń"
    for _ in range(2):
        DeviceReport.objects.create(kind="missing_aed", description="Brak AED", contact_email="a@example.pl")
    operator = Integration.objects.create(
        slug="szpital-x", name="Szpital X", connector="operator_file", publisher="Szpital Wojewódzki X", format="csv"
    )
    SourceRecord.objects.create(integration=operator, source_record_id="1", content_hash="x")
    rows = protected_data_rows()
    assert rows[0]["Rozmiar danych"] == "2 zgłoszenia"
    operator_row = rows[1]
    assert "Szpital Wojewódzki X" in operator_row["Zasób chronionych danych"]
    assert operator_row["Format danych"] == "CSV" and operator_row["Rozmiar danych"] == "1 rekord"
    assert [row["Lp."] for row in rows] == [1, 2, 3]
    assert rows[2]["Rozmiar danych"].endswith("1 rekord źródłowy")

    # a disabled operator is no longer listed; the served file follows a new data version
    operator.enabled = False
    operator.save()
    bump_data_version()
    sheet = _sheet(Client().get("/api/export/wykaz-chronionych-danych.xlsx").content)
    assert sheet.max_row == 3 and "Szpital" not in str(sheet["B3"].value)
