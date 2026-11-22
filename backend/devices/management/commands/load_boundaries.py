"""Load municipality and town boundaries (PRG, GUGiK) and fill `teryt` / `city` of devices from their coordinates.

    manage.py load_boundaries                 # download the layer (~70 MB, once) into var/boundaries/ and load it
    manage.py load_boundaries --if-missing    # do nothing when boundaries are already loaded (dev start, deploys)
    manage.py load_boundaries --file PATH     # a local A05_Granice_jednostek_ewidencyjnych shapefile (no suffix)
    manage.py load_boundaries --download      # fetch the layer again (PRG is republished a few times a year)

See devices/boundaries.py for what is filled and when it is left empty.
"""

import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from devices import boundaries
from devices.cache import bump_data_version
from devices.exports import rebuild_all
from devices.merge import recompute
from devices.models import Device


class Command(BaseCommand):
    help = "Load PRG municipality boundaries and geocode devices' teryt and city from their coordinates"

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Local shapefile path without suffix (default: download from PRG)")
        parser.add_argument("--download", action="store_true", help="Download the layer even if a copy exists")
        parser.add_argument("--if-missing", action="store_true", help="Skip when boundaries are already loaded")
        parser.add_argument("--no-recompute", action="store_true", help="Load only; devices update on the next sync")

    def handle(self, *args, **options):
        if options["if_missing"] and boundaries.loaded():
            self.stdout.write("Boundaries already loaded")
            return
        if options["file"]:
            path = Path(options["file"])
        else:
            path = settings.VAR_DIR / "boundaries" / boundaries.LAYER
            if options["download"] or not path.with_suffix(".shp").exists():
                self.stdout.write(f"Downloading {boundaries.LAYER} from {boundaries.PRG_URL} (~70 MB)")
                path = boundaries.download(path.parent)
        started = time.monotonic()
        count = boundaries.load(path)
        self.stdout.write(f"Loaded {count} units in {time.monotonic() - started:.0f} s")
        if options["no_recompute"]:
            return
        started = time.monotonic()
        ids = list(Device.objects.filter(active=True).values_list("pk", flat=True))
        recompute(ids)
        bump_data_version()
        rebuild_all()
        filled = Device.objects.filter(active=True, field_sources__teryt__method="geocoded").count()
        towns = Device.objects.filter(active=True, field_sources__city__method="geocoded").count()
        self.stdout.write(
            f"Recomputed {len(ids)} devices and rebuilt exports in {time.monotonic() - started:.0f} s: "
            f"teryt geocoded for {filled}, city for {towns}"
        )
