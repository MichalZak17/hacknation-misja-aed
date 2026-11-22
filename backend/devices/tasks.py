from celery import shared_task

from .cache import bump_data_version
from .exports import rebuild_all
from .merge import recompute
from .models import Device


@shared_task
def rebuild_exports():
    rebuild_all()


@shared_task
def recompute_readiness():
    """Readiness changes with the calendar (something becomes due), not only with new data."""
    ids = list(Device.objects.exclude(readiness="unknown").values_list("id", flat=True))
    ids += list(
        Device.objects.filter(readiness="unknown")
        .exclude(pads_expiry_date__isnull=True, battery_expiry_date__isnull=True, next_inspection_due__isnull=True)
        .values_list("id", flat=True)
    )
    if ids:
        recompute(ids)
        bump_data_version()
        rebuild_all()
    return len(ids)
