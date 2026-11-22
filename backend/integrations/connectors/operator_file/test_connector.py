"""Operator file connector: reference-schema columns by field name or Polish label."""


def test_operator_file_csv(parse_feed):
    raw = (
        "id,Szerokość geograficzna,lon,serial_number,Ważność elektrod,battery_expiry_date,access,Producent\n"
        "OP-1,52.2297,21.0122,SN-001,2027-06-30,2028-01-01,public,Philips\n"
        ",52.23,21.01,,31.12.2026,not-a-date,sometimes,\n"
    ).encode()
    records, _ = parse_feed("operator_file", raw, config={})
    assert records[0].source_record_id == "OP-1"
    assert records[0].data["serial_number"] == "SN-001"
    assert records[0].data["pads_expiry_date"] == "2027-06-30"
    assert records[0].data["manufacturer"] == "Philips"
    assert records[1].source_record_id == "row-3" and "missing_id" in records[1].issues
    assert records[1].data["pads_expiry_date"] == "2026-12-31"
    assert "bad_date:battery_expiry_date" in records[1].issues
    assert "bad_value:access" in records[1].issues


def _filled_template(rows: list[dict]) -> list[list[str]]:
    """The reference scope template's header (Polish labels) with these rows instead of the examples."""
    from devices.reference_scope import template_header, template_row

    return [template_header()] + [template_row(row) for row in rows]


def _example(**changes) -> dict:
    from devices.reference_scope import EXAMPLE_ROWS

    return EXAMPLE_ROWS[0] | changes


def test_template_csv_uploads_as_is(parse_feed):
    """The CSV template with its Polish headers parses as is; the example rows left in are skipped."""
    from devices.reference_scope import build_template_csv

    records, _ = parse_feed("operator_file", build_template_csv(), config={})
    assert records == []
    filled = build_template_csv() + b"OP-7,50.1,19.9,,,,,,,public,operational\r\n"
    (record,) = parse_feed("operator_file", filled, config={})[0]
    assert record.source_record_id == "OP-7" and record.lat == 50.1
    assert record.data["access"] == "public" and record.data["operational_status"] == "operational"


def test_template_xlsx_with_polish_headers(parse_feed):
    """A filled-in schema.xlsx: first sheet, Polish headers, every reference field read with its type."""
    import io

    from openpyxl import load_workbook

    from devices.reference_scope import EXAMPLE_ROWS, build_reference_xlsx

    workbook = load_workbook(io.BytesIO(build_reference_xlsx()))
    sheet = workbook.worksheets[0]
    sheet.delete_rows(3, len(EXAMPLE_ROWS))  # keep one example row, given a real id
    sheet["A2"] = "OP-1"
    buffer = io.BytesIO()
    workbook.save(buffer)

    (record,) = parse_feed("operator_file", buffer.getvalue(), config={})[0]
    example = EXAMPLE_ROWS[0]
    assert record.source_record_id == "OP-1" and not record.issues
    assert (record.lat, record.lon) == (float(example["lat"]), float(example["lon"]))
    data = record.data
    assert data["serial_number"] == example["serial_number"] and data["operator_regon"] == "123456785"
    assert data["teryt"] == "1261011" and data["simc"] == "0950463" and data["postal_code"] == "30-001"
    assert data["address"] == "ul. Przykładowa 1" and data["pads_expiry_date"] == "2027-05-31"
    assert data["indoor"] is True and data["seasonal"] is False and data["coordinate_accuracy_m"] == 3.0
    assert data["access_conditions"] == ["ask_staff_or_security", "only_during_opening_hours"]
    assert data["last_self_test_at"] == "2026-11-20T02:00:00+00:00"
    assert "readiness" not in data and "sources" not in data  # computed by the merge, not taken from a file


def test_technical_and_polish_headers_are_equivalent(parse_feed):
    import csv
    import io

    from devices.reference_scope import template_columns

    rows = _filled_template([_example(id="OP-1")])
    by_label = io.StringIO()
    csv.writer(by_label).writerows(rows)
    by_name = io.StringIO()
    csv.writer(by_name).writerows([[c.name for c in template_columns()]] + rows[1:])
    polish = parse_feed("operator_file", by_label.getvalue().encode(), config={})[0][0]
    technical = parse_feed("operator_file", by_name.getvalue().encode(), config={})[0][0]
    assert polish.data == technical.data and polish.data["model"] == "HeartStart FRx"


def test_operator_values_are_checked(parse_feed):
    import csv
    import io

    buffer = io.StringIO()
    csv.writer(buffer).writerows(
        [
            ["id", "lat", "lon", "access_conditions", "last_self_test_at", "teryt"],
            ["OP-1", "50.1", "19.9", "key_holder, teleport", "2026-11-20T03:00", "1261011"],
            ["OP-2", "50.1", "19.9", "", "wczoraj", ""],
        ]
    )
    first, second = parse_feed("operator_file", buffer.getvalue().encode(), config={})[0]
    assert first.data["access_conditions"] == ["key_holder"] and "bad_value:access_conditions" in first.issues
    assert first.data["last_self_test_at"] == "2026-11-20T02:00:00+00:00"  # no offset: Polish time
    assert "bad_date:last_self_test_at" in second.issues and "last_self_test_at" not in second.data


def test_access_conditions_as_true_false_columns(parse_feed):
    """The template's one column per condition (technical name or Polish label, any case) builds the list; a single
    list column still works and the two merge."""
    import csv
    import io

    buffer = io.StringIO()
    csv.writer(buffer).writerows(
        [
            [
                "id",
                "lat",
                "lon",
                "access_conditions_key_holder",
                "WARUNEK DOSTĘPU: TYLKO DLA PERSONELU",
                "access_conditions_call_phone",
                "access_conditions",
            ],
            ["OP-1", "50.1", "19.9", "true", "tak", "false", ""],
            ["OP-2", "50.1", "19.9", "false", "false", "false", ""],
            ["OP-3", "50.1", "19.9", "", "", "true", "only_during_events"],
        ]
    )
    first, second, third = parse_feed("operator_file", buffer.getvalue().encode(), config={})[0]
    assert first.data["access_conditions"] == ["key_holder", "staff_only"] and not first.issues
    assert second.data.get("access_conditions") is None
    assert third.data["access_conditions"] == ["only_during_events", "call_phone"]
