"""Write the reference data scope deliverable (wzorcowy zakres danych): the XLSX workbook, the single-sheet XLSX template
and the CSV template, the same files /api/export/schema.xlsx, schema-template.xlsx and schema-template.csv serve. Needs
no database."""

from pathlib import Path

from django.core.management.base import BaseCommand

from devices.reference_scope import build_reference_xlsx, build_template_csv, build_template_xlsx

NAME = "wzorcowy-zakres-danych-aed"


class Command(BaseCommand):
    help = "Write wzorcowy-zakres-danych-aed.xlsx, -szablon.xlsx and .csv into a directory"

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path)

    def handle(self, directory: Path, **options):
        directory.mkdir(parents=True, exist_ok=True)
        files = (
            (".xlsx", build_reference_xlsx()),
            ("-szablon.xlsx", build_template_xlsx()),
            (".csv", build_template_csv()),
        )
        for suffix, content in files:
            path = directory / f"{NAME}{suffix}"
            path.write_bytes(content)
            self.stdout.write(f"{path} ({len(content)} B)")
