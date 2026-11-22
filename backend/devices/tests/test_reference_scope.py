"""The single-sheet template for dane.gov.pl, the published scope without the address line, and the CSVW metadata of
aeds.csv."""

import csv
import io
import json

import pytest
from django.test import Client
from openpyxl import load_workbook

from devices.reference_scope import (
    EXAMPLE_ROWS,
    TEMPLATE_SHEET,
    build_csvw_metadata,
    build_reference_txt,
    build_template_csv,
    template_columns,
    template_header,
)
from devices.tests.test_api import seeded  # noqa: F401 — the krosno fixture feed, synced


def test_published_scope_has_no_address_line_and_flat_access_conditions():
    names = [c.name for c in template_columns()]
    assert "address" not in names and "access_conditions" not in names
    assert {"street_type", "street", "house_number", "postal_code", "city"} <= set(names)
    assert "access_conditions_key_holder" in names
    header = next(csv.reader(io.StringIO(build_template_csv().decode("utf-8-sig"))))
    assert header == template_header() and "Adres" not in header
    txt = build_reference_txt().decode()
    assert "address — " not in txt and "access_conditions_staff_only — " in txt


def test_example_rows_flag_their_access_conditions():
    rows = list(csv.DictReader(io.StringIO(build_template_csv().decode("utf-8-sig"))))
    label = next(c.label for c in template_columns() if c.name == "access_conditions_ask_staff_or_security")
    other = next(c.label for c in template_columns() if c.name == "access_conditions_call_phone")
    assert rows[0][label] == "true" and rows[0][other] == "false"
    assert rows[2][label] == ""  # the level-1 example says nothing about access conditions


@pytest.mark.django_db
def test_template_xlsx_is_one_excel_table():
    response = Client().get("/api/export/schema-template.xlsx")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response["Content-Disposition"] == 'attachment; filename="wzorcowy-zakres-danych-aed-szablon.xlsx"'
    assert Client().head("/api/export/schema-template.xlsx").status_code == 200

    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == [TEMPLATE_SHEET]
    sheet = workbook.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    assert list(rows[0]) == template_header() and len(rows) == 1 + len(EXAMPLE_ROWS)
    assert "Adres" not in rows[0]
    (table,) = sheet.tables.values()
    assert table.ref == f"A1:{sheet.cell(row=1, column=len(rows[0])).column_letter}{len(rows)}"
    assert table.headerRowCount == 1 and table.tableStyleInfo.name
    assert not sheet.merged_cells.ranges and sheet.auto_filter.ref is None
    assert not sheet.data_validations.dataValidation
    assert not any(cell.comment for row in sheet.iter_rows() for cell in row)
    assert not any(isinstance(v, str) and v.startswith("=") for row in rows for v in row)  # no formulas
    names = [c.name for c in template_columns()]
    teryt, lat, floor = (names.index(n) + 1 for n in ("teryt", "lat", "floor"))
    assert sheet.cell(row=3, column=teryt).value == "0264011" and sheet.cell(row=3, column=teryt).number_format == "@"
    assert isinstance(sheet.cell(row=2, column=lat).value, float) and sheet.cell(row=2, column=floor).value == 0
    props = workbook.properties
    assert props.title == "Wzorcowy zakres danych AED" and props.language == "pl-PL" and props.creator
    assert props.subject


@pytest.mark.django_db
def test_reference_xlsx_first_sheet_is_a_table_too():
    workbook = load_workbook(io.BytesIO(Client().get("/api/export/schema.xlsx").content))
    sheet = workbook.worksheets[0]
    assert len(sheet.tables) == 1 and sheet.auto_filter.ref is None
    assert workbook.properties.title == "Wzorcowy zakres danych AED"


@pytest.mark.django_db
def test_csvw_metadata_describes_the_csv(seeded, settings):  # noqa: F811
    settings.PUBLIC_BASE_URL = "https://aed.example.pl"
    client = Client()
    csv_response = client.get("/api/export/aeds.csv")
    assert csv_response["Link"] == (
        '<https://aed.example.pl/api/export/aeds.csv-metadata.json>; rel="describedby"; type="application/csvm+json"'
    )
    header = next(csv.reader(io.StringIO(csv_response.content.decode("utf-8-sig"))))

    response = client.get("/api/export/aeds.csv-metadata.json")
    assert response.status_code == 200 and response["Content-Type"] == "application/csvm+json"
    assert not response.has_header("Content-Disposition")
    assert client.head("/api/export/aeds.csv-metadata.json").status_code == 200
    assert (
        client.get("/api/export/aeds.csv-metadata.json", headers={"If-None-Match": response["ETag"]}).status_code == 304
    )
    body = json.loads(response.content)
    assert body["@context"] == ["http://www.w3.org/ns/csvw", {"@language": "pl"}]
    assert body["url"] == "https://aed.example.pl/api/export/aeds.csv"
    assert body["null"] == ["."] and body["dc:title"] and body["dc:license"]["@id"].startswith("https://")
    schema = body["tableSchema"]
    assert [c["name"] for c in schema["columns"]] == header  # same columns, same order
    assert schema["primaryKey"] == "id" and schema["aboutUrl"] == "https://aed.example.pl/api/v1/aeds/{id}"
    columns = {c["name"]: c for c in schema["columns"]}
    assert columns["id"]["required"] is True and columns["id"]["titles"] == "Identyfikator AED"
    assert columns["lat"]["datatype"] == "decimal" and columns["lat"]["propertyUrl"] == "https://schema.org/latitude"
    assert all(c["dc:description"] for c in schema["columns"])


def test_csvw_datatypes():
    body = build_csvw_metadata(
        "https://aed.example.pl/",
        ["id", "floor", "verified_on", "last_self_test_at", "indoor", "access_conditions_key_holder", "teryt", "x"],
    )
    types = {c["name"]: c["datatype"] for c in body["tableSchema"]["columns"]}
    boolean = {"base": "boolean", "format": "true|false"}
    assert types == {
        "id": "string",
        "floor": "integer",
        "verified_on": "date",
        "last_self_test_at": "dateTime",
        "indoor": boolean,
        "access_conditions_key_holder": boolean,
        "teryt": "string",
        "x": "string",  # a column the reference scope does not know yet
    }
    assert body["url"] == "https://aed.example.pl/api/export/aeds.csv"
