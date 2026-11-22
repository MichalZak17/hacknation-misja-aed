"""Readiness: can this AED be relied on today, from what its owner has told us?

- expired:   out of service / decommissioned / missing, battery marked for replacement, or pads, battery or the
             inspection already overdue
- attention: battery low, or something falls due within READINESS_ATTENTION_DAYS
- ready:     pads or battery expiry known, and nothing due
- unknown:   no maintenance data — most open-data records, which only locate the device
"""

from datetime import date, timedelta

from django.conf import settings


def compute_readiness(device, today: date | None = None) -> str:
    today = today or date.today()
    soon = today + timedelta(days=settings.READINESS_ATTENTION_DAYS)
    if device.operational_status in {"out_of_service", "decommissioned", "missing"}:
        return "expired"
    if device.battery_status == "replace":
        return "expired"
    due_dates = [d for d in (device.pads_expiry_date, device.battery_expiry_date, device.next_inspection_due) if d]
    if any(d < today for d in due_dates):
        return "expired"
    if device.battery_status == "low" or any(d <= soon for d in due_dates):
        return "attention"
    if device.pads_expiry_date or device.battery_expiry_date:
        return "ready"
    return "unknown"
