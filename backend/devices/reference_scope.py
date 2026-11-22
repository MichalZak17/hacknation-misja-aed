"""The reference data scope (wzorcowy zakres danych) as a data holder receives it: an XLSX whose first sheet is the
template itself (readable Polish headers, then example rows), followed by the field dictionary, the allowed values and
instructions; the template alone as a single-sheet XLSX (the file for dane.gov.pl: one sheet, one Excel table); and the
same template as CSV. Shaped after the ministry's own reference scopes on dane.gov.pl, which
ship one "wzorcowy zakres danych" sheet plus a UTF-8 CSV. The portal converts only the first sheet of an XLSX.

A filled-in template uploads as is: the operator_file connector reads both the Polish headers and the technical names.

Tables carry the published scope (PUBLISHED_SCHEMA: no one-line address) with one elementary value per cell: a list
field (access_conditions) becomes one true/false column per allowed value (schema.list_columns).

Also the CSVW metadata (W3C Model for Tabular Data) of the nationwide CSV, which the Standard techniczny §4.3 asks for
at 4★.
"""

import csv
import io
import json
from dataclasses import dataclass

from .schema import (
    BOOL_FIELDS,
    BOOL_VALUES,
    DATE_FIELDS,
    DATETIME_FIELDS,
    DESCRIPTIONS,
    FLOAT_FIELDS,
    LIST_FIELDS,
    NUMBER_FIELDS,
    PUBLISHED_SCHEMA,
    REQUIRED_FIELDS,
    SCHEMA,
    SchemaField,
    allowed_values,
    field_format,
    field_type,
    list_columns,
)

LEVELS = {1: "1 — podstawowy", 2: "2 — rozszerzony", 3: "3 — pełny"}
LEVEL_HINTS = {
    1: "wystarcza, żeby znaleźć urządzenie i wiedzieć, czy można z niego skorzystać",
    2: "dostępność (godziny, warunki) i dokładne miejsce w obiekcie",
    3: "dane sprzętowe i serwisowe dysponenta: elektrody, bateria, przeglądy",
}

TEMPLATE_SHEET = "Wzorcowy zakres danych"
TEMPLATE_TABLE = "WzorcowyZakresDanych"  # Excel table names allow no spaces
EXAMPLE_PREFIX = "PRZYKLAD-"
INTEGER_FIELDS = {"floor"}

# Illustrative rows: fictional streets ("Przykładowa"), example.org addresses, a REGON that only passes the checksum and
# a phone number that belongs to nobody. Row 1 fills all three levels, row 2 levels 1–2 and part of 3, row 3 level 1.
EXAMPLE_ROWS: list[dict[str, str]] = [
    {
        "id": "PRZYKLAD-001",
        "lat": "50.06143",
        "lon": "19.93658",
        "street_type": "ul.",
        "street": "Przykładowa",
        "house_number": "1",
        "postal_code": "30-001",
        "city": "Kraków",
        "teryt": "1261011",
        "access": "public",
        "operational_status": "operational",
        "readiness": "ready",
        "verified_on": "2026-11-18",
        "sources": "przyklad-dysponent",
        "building_name": "Przykładowa Szkoła Podstawowa nr 1",
        "location_detail": "Hol główny, obok portierni",
        "floor": "0",
        "indoor": "true",
        "placement": "inside_building",
        "opening_hours": "Mo-Fr 07:00-17:00",
        "opening_hours_raw": "pon.–pt. 7:00–17:00",
        "access_conditions": "ask_staff_or_security;only_during_opening_hours",
        "seasonal": "false",
        "cabinet": "alarm",
        "is_mobile": "false",
        "photo_url": "https://example.org/aed/przyklad-001.jpg",
        "coordinate_method": "gps",
        "coordinate_accuracy_m": "3",
        "pads_type": "universal",
        "pediatric_pads_available": "false",
        "pediatric_mode": "true",
        "serial_number": "PRZYKLAD-SN-0001",
        "manufacturer": "Philips",
        "model": "HeartStart FRx",
        "inventory_number": "INW/2023/001",
        "manufactured_on": "2023-04-12",
        "installed_on": "2023-06-01",
        "pads_replaced_on": "2025-05-21",
        "pads_expiry_date": "2027-05-31",
        "battery_installed_on": "2023-06-01",
        "battery_expiry_date": "2027-06-01",
        "battery_status": "ok",
        "last_self_test_at": "2026-11-20T02:00:00Z",
        "last_self_test_result": "pass",
        "last_inspection_on": "2026-06-01",
        "next_inspection_due": "2027-06-01",
        "last_used_on": "2025-05-20",
        "verification_method": "inspekcja na miejscu",
        "operator_name": "Przykładowy Dysponent sp. z o.o.",
        "operator_regon": "123456785",
        "operator_contact": "+48120000000",
        "simc": "0950463",
    },
    {
        "id": "PRZYKLAD-002",
        "lat": "51.10789",
        "lon": "17.03854",
        "street_type": "al.",
        "street": "Przykładowa",
        "house_number": "15a",
        "postal_code": "50-001",
        "city": "Wrocław",
        "teryt": "0264011",
        "access": "public",
        "operational_status": "operational",
        "readiness": "unknown",
        "verified_on": "2026-09-03",
        "sources": "przyklad-gmina",
        "building_name": "Przykładowe Centrum Sportu",
        "location_detail": "Ściana przy wejściu głównym",
        "floor": "0",
        "indoor": "false",
        "placement": "outside_on_building",
        "opening_hours": "24/7",
        "opening_hours_raw": "całą dobę",
        "access_conditions": "siren_or_alarm_button",
        "seasonal": "false",
        "cabinet": "alarm",
        "is_mobile": "false",
        "coordinate_method": "geocoded",
        "coordinate_accuracy_m": "15",
        "pads_type": "adult",
        "pediatric_pads_available": "true",
        "pediatric_mode": "false",
        "manufacturer": "ZOLL",
        "model": "AED Plus",
        "operator_name": "Przykładowy Ośrodek Sportu",
        "operator_regon": "12345678500010",
        "operator_contact": "aed@example.org",
        "simc": "0986283",
    },
    {
        "id": "PRZYKLAD-003",
        "lat": "54.35205",
        "lon": "18.64637",
        "street_type": "ul.",
        "street": "Przykładowa",
        "house_number": "7/2",
        "postal_code": "80-001",
        "city": "Gdańsk",
        "teryt": "2261011",
        "access": "limited",
        "operational_status": "operational",
        "readiness": "unknown",
        "verified_on": "2025-12-10",
        "sources": "przyklad-rejestr",
    },
]


@dataclass(frozen=True)
class Column:
    """One table column: a published field, or one value of a list field as a true/false column."""

    name: str  # technical name
    label: str  # Polish header
    field: SchemaField
    value: str = ""  # the list value a true/false column stands for

    def text(self, row: dict[str, str]) -> str:
        """The cell's text in an example row. A list column is true when the row lists the value, false when it lists
        others, and empty (no data) when the row says nothing about the list."""
        raw = row.get(self.field.field, "")
        if not self.value:
            return raw
        return ("true" if self.value in raw.split(";") else "false") if raw else ""

    def type_label(self) -> str:
        return "logiczny" if self.value else field_type(self.field)

    def format(self) -> str:
        return "true albo false" if self.value else field_format(self.field)

    def description(self) -> str:
        if self.value:
            return (
                f"true, gdy dostęp do AED wymaga tego warunku, false, gdy nie wymaga. W JSON, GeoJSON i API ten "
                f"warunek to wartość {self.value} na liście {self.field.field}."
            )
        return DESCRIPTIONS[self.field.field]

    def allowed(self) -> list[tuple[str, str]]:
        return BOOL_VALUES if self.value else allowed_values(self.field.field)

    @property
    def required(self) -> bool:
        return not self.value and self.field.field in REQUIRED_FIELDS


def template_columns() -> list[Column]:
    """The columns of every table we publish, in schema order: the published scope, list fields flattened."""
    columns = []
    for f in PUBLISHED_SCHEMA:
        if f.field in LIST_FIELDS:
            columns += [Column(name, label, f, value) for name, label, value in list_columns(f.field)]
        else:
            columns.append(Column(f.field, f.label, f))
    return columns


def _all_columns() -> dict[str, Column]:
    """Every column a table of ours may have, by technical name, including internal and unflattened fields."""
    return {f.field: Column(f.field, f.label, f) for f in SCHEMA} | {c.name: c for c in template_columns()}


def template_header() -> list[str]:
    return [c.label for c in template_columns()]


def template_row(row: dict[str, str]) -> list[str]:
    """A record (technical field names, lists joined with ";") as a template row."""
    return [c.text(row) for c in template_columns()]


def build_template_csv() -> bytes:
    """The template as CSV: RFC 4180 (comma, CRLF, quotes where needed), UTF-8 with a BOM so Excel reads it."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(template_header())
    for row in EXAMPLE_ROWS:
        writer.writerow(template_row(row))
    return ("﻿" + buffer.getvalue()).encode()


def example(column: Column) -> str:
    """The dictionary's example: the first example row, so the sheets agree with each other."""
    return column.text(EXAMPLE_ROWS[0]) or column.field.example


def _allowed_text(column: Column) -> str:
    return "\n".join(f"{value} — {meaning}" for value, meaning in column.allowed())


def _cell_value(column: Column, text: str):
    """Numbers stay numbers; everything else is written as text, so dates, booleans and codes keep their spelling."""
    if not text:
        return None
    if column.field.field in NUMBER_FIELDS:
        return float(text) if "." in text else int(text)
    if column.field.field in INTEGER_FIELDS:
        return int(text)
    return text


def _number_format(column: Column) -> str:
    field = column.field.field
    if field in {"lat", "lon"}:
        return "0.00000"
    if field in NUMBER_FIELDS | INTEGER_FIELDS:
        return "0"
    return "@"  # text: codes keep their leading zeros


def _add_table(sheet, columns: int, rows: int, stripes: bool) -> None:
    """The data range as an Excel table with a marked header row (accessibility: read as a table, not loose cells)."""
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    table = Table(displayName=TEMPLATE_TABLE, ref=f"A1:{get_column_letter(columns)}{rows + 1}", headerRowCount=1)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=stripes, showColumnStripes=False)
    sheet.add_table(table)


def _set_properties(workbook, subject: str) -> None:
    props = workbook.properties
    props.title = "Wzorcowy zakres danych AED"
    props.subject = subject
    props.creator = "Misja AED"
    props.keywords = "AED; defibrylator; wzorcowy zakres danych; dane.gov.pl"
    props.language = "pl-PL"


def build_template_xlsx() -> bytes:
    """The template alone, for dane.gov.pl (Standard techniczny §3.1): one sheet, one header row, the example rows, all
    as one Excel table; no merged cells, comments, formulas, validation, filters or anything outside the table. Codes
    are text cells, so leading zeros survive. Black on white (stripes light grey): contrast well above 4.5:1."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment
    from openpyxl.utils import get_column_letter

    columns = template_columns()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = TEMPLATE_SHEET
    sheet.append(template_header())
    for row in EXAMPLE_ROWS:
        sheet.append([_cell_value(c, c.text(row)) for c in columns])
    for index, column in enumerate(columns, start=1):
        letter = get_column_letter(index)
        number_format = _number_format(column)
        sheet.column_dimensions[letter].number_format = number_format  # also rows typed in later
        for row_index in range(2, len(EXAMPLE_ROWS) + 2):
            sheet.cell(row=row_index, column=index).number_format = number_format
        sheet.cell(row=1, column=index).alignment = Alignment(wrap_text=True, vertical="top")
        longest = max([min(len(column.label), 30)] + [len(column.text(r)) for r in EXAMPLE_ROWS])
        sheet.column_dimensions[letter].width = min(max(longest + 3, 14), 48)
    sheet.freeze_panes = "A2"
    _add_table(sheet, len(columns), len(EXAMPLE_ROWS), stripes=True)
    _set_properties(
        workbook, "Szablon danych o defibrylatorach AED: jeden wiersz nagłówków, jeden wiersz na urządzenie"
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_reference_xlsx() -> bytes:
    """The deliverable workbook: the template (an Excel table, colour per level, dropdowns), then the field
    dictionary, the allowed values and instructions. The portal file is build_template_xlsx (the first sheet alone)."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    bold = Font(bold=True)
    header_font = Font(bold=True, color="FFFFFF")
    # White on these: 9.5:1, 7.1:1 and 4.6:1 (WCAG AA needs 4.5:1)
    level_fills = {
        1: PatternFill("solid", fgColor="8B1E2D"),
        2: PatternFill("solid", fgColor="4A5A6A"),
        3: PatternFill("solid", fgColor="6B7B3A"),
    }
    example_fill = PatternFill("solid", fgColor="FFF4D6")
    wrap_top = Alignment(wrap_text=True, vertical="top")
    thin = Border(bottom=Side(style="thin", color="999999"))
    template_rows = 1000  # validation lists and text format reach this far down
    template = template_columns()

    workbook = Workbook()

    # 1. The template: what a data holder fills and publishes
    sheet = workbook.active
    sheet.title = TEMPLATE_SHEET
    sheet.append(template_header())
    for row in EXAMPLE_ROWS:
        sheet.append([_cell_value(c, c.text(row)) for c in template])
    for index, column in enumerate(template, start=1):
        f = column.field
        letter = get_column_letter(index)
        header = sheet.cell(row=1, column=index)
        header.font = header_font
        header.fill = level_fills[f.level]
        header.alignment = Alignment(wrap_text=True, vertical="center")
        required = " Pole wymagane." if column.required else ""
        header.comment = Comment(
            f"{column.name} · poziom {LEVELS[f.level]}{required}\n{column.label}: {column.format()}.",
            "Misja AED",
            120,
            260,
        )
        number_format = _number_format(column)
        sheet.column_dimensions[letter].number_format = number_format  # also new rows typed in later
        for row_index in range(2, len(EXAMPLE_ROWS) + 2):
            cell = sheet.cell(row=row_index, column=index)
            cell.number_format = number_format
            cell.fill = example_fill
        longest = max([min(len(column.label), 30)] + [len(column.text(r)) for r in EXAMPLE_ROWS])
        sheet.column_dimensions[letter].width = min(max(longest + 3, 12), 48)
        values = [v for v, _ in column.allowed()]
        if values:
            validation = DataValidation(
                type="list",
                formula1='"' + ",".join(values) + '"',
                allow_blank=True,
                showErrorMessage=True,
                errorTitle=column.label[:32],
                error="Wybierz wartość z listy (arkusz „Dozwolone wartości”).",
                promptTitle=column.label[:32],
                prompt="true albo false" if column.allowed() is BOOL_VALUES else "Wybierz z listy",
            )
            validation.add(f"{letter}2:{letter}{template_rows + 1}")
            sheet.add_data_validation(validation)
    sheet.row_dimensions[1].height = 45
    sheet.freeze_panes = "B2"
    _add_table(sheet, len(template), len(EXAMPLE_ROWS), stripes=False)  # the table brings its own filter buttons

    # 2. The field dictionary
    dictionary = workbook.create_sheet("Słownik pól")
    columns = [
        ("Nagłówek kolumny", 30),
        ("Nazwa techniczna", 26),
        ("Opis", 60),
        ("Typ", 12),
        ("Format", 40),
        ("Poziom", 16),
        ("Wymagane", 11),
        ("Dozwolone wartości", 60),
        ("Przykład", 30),
    ]
    dictionary.append([name for name, _ in columns])
    for column in template:
        dictionary.append(
            [
                column.label,
                column.name,
                column.description(),
                column.type_label(),
                column.format(),
                LEVELS[column.field.level],
                "tak" if column.required else "nie",
                _allowed_text(column),
                example(column),
            ]
        )
    _style_table(dictionary, columns, bold, thin, wrap_top)

    # 3. Allowed values, one per row (easier to filter and to use as a lookup)
    values_sheet = workbook.create_sheet("Dozwolone wartości")
    columns = [("Nagłówek kolumny", 30), ("Nazwa techniczna", 26), ("Wartość", 28), ("Znaczenie", 80)]
    values_sheet.append([name for name, _ in columns])
    for column in template:
        for value, meaning in column.allowed():
            values_sheet.append([column.label, column.name, value, meaning])
    _style_table(values_sheet, columns, bold, thin, wrap_top)

    # 4. Instructions
    guide = workbook.create_sheet("Instrukcja")
    guide.column_dimensions["A"].width = 4
    guide.column_dimensions["B"].width = 120
    for line in INSTRUCTIONS:
        if line.startswith("# "):
            guide.append(["", line[2:]])
            guide.cell(row=guide.max_row, column=2).font = Font(bold=True, size=13 if guide.max_row == 1 else 11)
        else:
            guide.append(["", line])
            guide.cell(row=guide.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    workbook.active = 0
    _set_properties(workbook, "Szablon, słownik pól i dozwolone wartości danych o defibrylatorach AED")
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _style_table(sheet, columns, bold, border, alignment) -> None:
    from openpyxl.utils import get_column_letter

    for index, (_, width) in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for cell in sheet[1]:
        cell.font = bold
        cell.border = border
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = alignment
            cell.number_format = "@"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def build_reference_txt() -> bytes:
    """The field dictionary as plain text: dane.gov.pl accepts supplements only as doc/docx/pdf/txt/odt."""
    template = template_columns()
    lines = [
        "Wzorcowy zakres danych AED — słownik pól",
        "",
        "Poziomy: " + "; ".join(f"{LEVELS[level]}: {hint}" for level, hint in LEVEL_HINTS.items()) + ".",
        "Pola wymagane: " + ", ".join(c.name for c in template if c.required) + ". Pozostałe pola mogą być puste: "
        "w szablonie puste pole oznacza brak danych, w zbiorze ogólnokrajowym (aeds.csv) brak danych oznacza znak "
        "umowny „.” (kropka).",
        "Daty rrrr-mm-dd, data i czas w UTC rrrr-mm-ddThh:mm:ssZ, wartości logiczne true/false, kropka dziesiętna, "
        "współrzędne EPSG:4326.",
        "Jedna wartość w jednym polu: adres w osobnych polach (cecha ulicy, nazwa ulicy, numer budynku, kod pocztowy, "
        "miejscowość), a każdy warunek dostępu w osobnej kolumnie true/false (access_conditions_…). W JSON, GeoJSON i "
        "API warunki dostępu są listą access_conditions.",
        "W szablonie (XLSX, CSV) kolumny mają nagłówki z nazwy polskiej; zbiór ogólnokrajowy (aeds.csv) używa nazw "
        "technicznych w tej samej kolejności i pomija kolumny, których nie wypełnia jeszcze żaden rekord. Opis "
        "kolumn aeds.csv w modelu W3C CSVW: aeds.csv-metadata.json.",
        "",
    ]
    for column in template:
        required = "tak" if column.required else "nie"
        lines.append(f"{column.name} — {column.label}")
        lines.append(f"    {column.description()}")
        lines.append(
            f"    typ: {column.type_label()}; format: {column.format()}; poziom: {LEVELS[column.field.level]}; "
            f"wymagane: {required}"
        )
        lines.append(f"    przykład: {example(column)}")
        for value, meaning in column.allowed():
            lines.append(f"      {value} — {meaning}")
        lines.append("")
    return "\r\n".join(lines).encode()


INSTRUCTIONS = [
    "# Wzorcowy zakres danych AED — instrukcja dla dysponenta",
    "Szablon opisuje jeden rekord na urządzenie AED. Ten sam zakres publikuje ogólnokrajowy zbiór „Defibrylatory AED "
    "w Polsce” na dane.gov.pl, więc plik wypełniony według szablonu da się połączyć z danymi innych dysponentów.",
    "",
    "# Arkusze",
    "„Wzorcowy zakres danych” — szablon do wypełnienia: jeden wiersz nagłówków, potem jeden wiersz na urządzenie.",
    "„Słownik pól” — opis, typ, format, poziom i przykład każdej kolumny; tu jest też nazwa techniczna kolumny.",
    "„Dozwolone wartości” — wartości pól słownikowych i ich znaczenie.",
    "",
    "# Jak wypełnić",
    "1. Usuń trzy wiersze przykładowe (identyfikatory PRZYKLAD-…, żółte tło). Zawierają dane fikcyjne.",
    "2. Nie zmieniaj nazw ani kolejności kolumn i nie dodawaj wierszy nad nagłówkiem. Nagłówki polskie i nazwy "
    "techniczne (arkusz „Słownik pól”) są równoważne.",
    "3. Pola wymagane: Identyfikator AED, Szerokość geograficzna, Długość geograficzna, Dostępność, Stan urządzenia. "
    "Pozostałe wypełnij, jeśli je znasz. Puste pole oznacza brak danych: nie wpisuj „brak”, „-” ani „nie dotyczy”. W "
    "polach słownikowych wpisz unknown, gdy wartość jest nieznana.",
    "4. Poziomy (kolor nagłówka): 1 podstawowy (bordowy) — wystarcza, żeby znaleźć AED i wiedzieć, czy można z niego "
    "skorzystać; 2 rozszerzony (szary) — godziny i warunki dostępu, dokładne miejsce w obiekcie; 3 pełny (oliwkowy) — "
    "dane sprzętowe i serwisowe: elektrody, bateria, przeglądy.",
    "5. Formaty: daty rrrr-mm-dd; data i czas w UTC rrrr-mm-ddThh:mm:ssZ; wartości logiczne true albo false; liczby z "
    "kropką dziesiętną, bez separatora tysięcy; współrzędne WGS84 (EPSG:4326) z co najmniej 5 miejscami po przecinku; "
    "kod pocztowy dd-ddd; REGON 9 albo 14 cyfr; telefon +48 i 9 cyfr, bez spacji.",
    "6. Kolumny z kodami i numerami (TERYT, SIMC, kod pocztowy, REGON, telefon, numer budynku) mają format tekstowy, "
    "żeby nie znikały zera na początku. Nie zmieniaj go.",
    "7. Jedna wartość w jednym polu. Warunki dostępu mają osobną kolumnę na każdy warunek (Warunek dostępu: …): "
    "wpisz true, gdy warunek obowiązuje, false, gdy nie; zostaw puste, jeśli nie wiesz.",
    "8. Adres: cecha ulicy, nazwa ulicy, numer budynku, kod pocztowy i miejscowość w osobnych kolumnach, nazwy w "
    "brzmieniu z rejestru TERYT. Nie łącz ich w jednym polu.",
    "9. Godziny dostępności zapisz w składni OpenStreetMap opening_hours (np. 24/7, Mo-Fr 08:00-16:00; "
    "Sa 09:00-13:00). Jeśli się nie da, wpisz je słowami w kolumnie Godziny dostępności (opis).",
    "10. Kontakt do dysponenta tylko instytucjonalny (telefon lub e-mail jednostki). Nie wpisuj danych osobowych.",
    "",
    "# Jak opublikować na dane.gov.pl",
    "1. Zapisz arkusz „Wzorcowy zakres danych” jako CSV UTF-8 (w Excelu: Plik › Zapisz jako › CSV UTF-8 (rozdzielany "
    "przecinkami)). CSV ma 3 gwiazdki otwartości, XLSX tylko 2.",
    "2. W panelu dostawcy dane.gov.pl dodaj zbiór: tytuł (np. „Defibrylatory AED — <nazwa dysponenta>”), opis, "
    "kategoria Zdrowie, słowa kluczowe (AED, defibrylator), częstotliwość aktualizacji i licencja (portal zaleca "
    "CC0 1.0).",
    "3. Dodaj zasób: plik CSV albo link do pliku na stronie dysponenta z włączoną automatyczną aktualizacją, żeby "
    "portal sam pobierał nowe wersje. Jako dokument dodatkowy możesz dołączyć ten słownik.",
    "4. Po walidacji pliku ustaw w tabeli typ „tekst” dla kolumn z kodami i numerami oraz typ „wartość logiczna” dla "
    "kolumn true/false.",
    "5. Żeby portal pokazał mapę, wskaż kolumny geolokalizacji: Szerokość geograficzna jako szerokość, Długość "
    "geograficzna jako długość, a Identyfikator AED lub Obiekt jako etykietę.",
    "",
    "# Przekazanie do zbioru ogólnokrajowego",
    "Wypełniony plik (XLSX albo CSV) można wgrać w panelu Misja AED jako import dysponenta bez żadnych zmian: polskie "
    "nagłówki i nazwy techniczne są rozpoznawane. Dane dysponenta mają pierwszeństwo przed danymi samorządów i "
    "OpenStreetMap.",
]


# ------------------------------------------------------------ CSVW metadata of aeds.csv
#
# W3C Model for Tabular Data and Metadata on the Web: what each column of the nationwide CSV means and how its values
# are typed, so csv2json / csv2rdf can turn the CSV into linked data (Standard techniczny §4.3, 4★ CSV). Served at
# aeds.csv-metadata.json, the location CSVW processors try first ({+url}-metadata.json), and announced by a Link
# header on the CSV.

# schema.org terms with an obvious match; other columns keep the CSVW default (the column name on the CSV's URL)
CSVW_PROPERTY_URLS = {
    "id": "https://schema.org/identifier",
    "lat": "https://schema.org/latitude",
    "lon": "https://schema.org/longitude",
    "postal_code": "https://schema.org/postalCode",
    "city": "https://schema.org/addressLocality",
    "building_name": "https://schema.org/name",
    "opening_hours": "https://schema.org/openingHours",
    "photo_url": "https://schema.org/image",
    "manufacturer": "https://schema.org/manufacturer",
    "model": "https://schema.org/model",
    "serial_number": "https://schema.org/serialNumber",
}
CSVW_NULL = "."  # the dataset's special sign (znak umowny) for "no data", written in every empty cell of aeds.csv


def _csvw_datatype(column: Column):
    field = column.field.field
    if column.value or field in BOOL_FIELDS:
        return {"base": "boolean", "format": "true|false"}
    if field in NUMBER_FIELDS | FLOAT_FIELDS:
        return "decimal"
    if field in INTEGER_FIELDS:
        return "integer"
    if field in DATE_FIELDS:
        return "date"
    if field in DATETIME_FIELDS:
        return "dateTime"
    if column.field.type == "url":
        return "anyURI"
    return "string"


def csv_columns() -> list[str]:
    """The header of the current aeds.csv: it leaves out the columns no record fills, so it varies with the data."""
    from .exports import get_export

    content, _ = get_export("csv")
    return next(csv.reader([content.split(b"\n", 1)[0].decode("utf-8-sig").rstrip("\r")]))


def build_csvw_metadata(base_url: str, columns: list[str] | None = None) -> dict:
    """The CSVW table description of /api/export/aeds.csv for the given (or the current) header."""
    from django.conf import settings

    from .exports import DATASET, PORTAL_LICENSES, attribution

    base = (base_url or settings.PUBLIC_BASE_URL or "").rstrip("/")
    known = _all_columns()
    described = []
    for name in csv_columns() if columns is None else columns:
        column = known.get(name)
        if column is None:  # a column added to the CSV but not to the reference scope yet
            described.append({"name": name, "titles": name, "datatype": "string"})
            continue
        entry = {
            "name": name,
            "titles": column.label,
            "dc:description": column.description(),
            "datatype": _csvw_datatype(column),
        }
        if column.required:
            entry["required"] = True
        if column.field.type == "string[]" and not column.value:
            entry["separator"] = ";"
        if name in CSVW_PROPERTY_URLS:
            entry["propertyUrl"] = CSVW_PROPERTY_URLS[name]
        described.append(entry)
    return {
        "@context": ["http://www.w3.org/ns/csvw", {"@language": "pl"}],
        "url": f"{base}/api/export/aeds.csv",
        "dc:title": DATASET["title"],
        "dc:license": {"@id": PORTAL_LICENSES.get(settings.DATASET_LICENSE, DATASET["license_url"])},
        "dc:rights": attribution(base),
        "dialect": {"encoding": "utf-8", "delimiter": ",", "header": True},
        "null": [CSVW_NULL],
        "tableSchema": {
            "columns": described,
            "primaryKey": "id",
            "aboutUrl": base + "/api/v1/aeds/{id}",
        },
    }


def build_csvw_json(base_url: str, columns: list[str] | None = None) -> bytes:
    return (json.dumps(build_csvw_metadata(base_url, columns), ensure_ascii=False, indent=2) + "\n").encode()
