"""Our list of protected data (wykaz chronionych danych, Data Governance Act art. 8): data Misja AED holds but does
not publish, which anyone may ask to re-use.

dane.gov.pl builds its nationwide table („Wykaz chronionych danych”, /dga/list-protected-data) every night from one
resource per public institution flagged `containsProtectedData` in its harvester XML. The portal rejects the whole XML
import when that resource's file is wrong, so the file follows its checks exactly:
- xlsx served with a Content-Type `mimetypes.guess_extension` maps to .xlsx (the CSV type with `; charset=utf-8`
  maps to nothing, which is why this is not a CSV);
- first sheet, header in row 1, exactly DGA_COLUMNS in this order and nothing else;
- no empty cell in „Zasób chronionych danych”, „Format danych” or „Rozmiar danych” (a row with one is dropped and the
  whole resource left out of the national table).
The portal adds the institution's name, renumbers „Lp.” and replaces the last column with „określone w ofercie”.

The rows are counted from the database whenever the exports are rebuilt, so the list keeps itself current: a new
operator file adds a row, the sizes follow the data.
"""

import io
import os

from django.conf import settings

# The portal's DGA_COLUMNS, word for word (mcod/resources/dga_constants.py)
DGA_COLUMNS = [
    "Lp.",
    "Zasób chronionych danych",
    "Format danych",
    "Rozmiar danych",
    "Warunki ponownego wykorzystywania",
]
DGA_SHEET = "Arkusz 1"
CONDITIONS = "Na wniosek; warunki określone indywidualnie w ofercie"
OPERATOR_CONNECTOR = "operator_file"
FORMAT_NAMES = {"geojson": "GeoJSON"}


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Polish noun form for a count: 1 zgłoszenie, 2 zgłoszenia, 5 zgłoszeń."""
    number = f"{n:,}".replace(",", "\u00a0")  # 19 080
    if n == 1:
        return f"{number} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{number} {few}"
    return f"{number} {many}"


def _format_name(fmt: str) -> str:
    return "/".join(FORMAT_NAMES.get(part, part.upper()) for part in fmt.lower().split("/"))


def _snapshot_bytes() -> int:
    total = 0
    for folder, _, files in os.walk(settings.SNAPSHOT_DIR):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(folder, name))
            except OSError:
                continue
    return total


def _megabytes(size: int) -> str:
    return f"{size / 1_000_000:.1f}".replace(".", ",") + " MB"


def protected_data_rows() -> list[dict]:
    """One dict per protected resource, keyed by DGA_COLUMNS. Every value is non-empty."""
    from integrations.models import Integration, SourceRecord, SyncRun

    from .models import DeviceReport

    rows = []

    reports = DeviceReport.objects.count()
    rows.append(
        {
            "Zasób chronionych danych": (
                "Zgłoszenia z formularza „Zgłoś AED” (brakujące, uszkodzone lub niedostępne defibrylatory, poprawki "
                "danych, zgłoszenia dysponentów): treść zgłoszenia, adres e-mail zgłaszającego, skrót adresu IP — dane "
                "osobowe"
            ),
            "Format danych": "CSV, JSON (eksport z bazy danych)",
            "Rozmiar danych": _plural(reports, "zgłoszenie", "zgłoszenia", "zgłoszeń"),
        }
    )

    operators = Integration.objects.filter(connector=OPERATOR_CONNECTOR, enabled=True).order_by("name")
    for integration in operators:
        records = SourceRecord.objects.filter(integration=integration, removed_at__isnull=True).count()
        holder = integration.publisher or integration.name
        rows.append(
            {
                "Zasób chronionych danych": (
                    f"Plik przekazany przez dysponenta AED: {holder} — pełna kopia z kolumnami spoza wzorcowego zakresu "
                    "danych, których nie publikujemy (np. dane kontaktowe osób odpowiedzialnych za urządzenia)"
                ),
                "Format danych": _format_name(integration.format or "csv/xlsx"),
                "Rozmiar danych": _plural(records, "rekord", "rekordy", "rekordów"),
            }
        )

    snapshots = SyncRun.objects.exclude(snapshot_path="").count()
    records = SourceRecord.objects.count()
    formats = sorted(
        {
            _format_name(i.format if i.format != "configurable" else "csv")
            for i in Integration.objects.filter(enabled=True)
            if i.format
        }
    )
    rows.append(
        {
            "Zasób chronionych danych": (
                "Archiwum surowych pobrań ze wszystkich źródeł (kopie plików w formacie źródła i rekordy źródłowe "
                "przed scaleniem) — objęte prawami podmiotów trzecich (licencje i prawa do baz danych dostawców)"
            ),
            "Format danych": ", ".join(formats or ["JSON"]) + " (kopie plików źródeł), JSON (rekordy w bazie danych)",
            "Rozmiar danych": (
                f"{_plural(snapshots, 'kopia pobrania', 'kopie pobrań', 'kopii pobrań')} "
                f"({_megabytes(_snapshot_bytes())}), {_plural(records, 'rekord źródłowy', 'rekordy źródłowe', 'rekordów źródłowych')}"
            ),
        }
    )

    for number, row in enumerate(rows, start=1):
        row["Lp."] = number
        row["Warunki ponownego wykorzystywania"] = CONDITIONS
    return rows


def build_dga_xlsx() -> bytes:
    """The list as the portal reads it: one sheet, the header in row 1, one row per resource, nothing else."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = DGA_SHEET
    sheet.append(DGA_COLUMNS)
    for row in protected_data_rows():
        sheet.append([row[column] for column in DGA_COLUMNS])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for column, width in zip("ABCDE", (6, 80, 30, 30, 40), strict=True):
        sheet.column_dimensions[column].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"
    workbook.properties.title = "Wykaz chronionych danych — Misja AED"
    workbook.properties.creator = "Misja AED"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
