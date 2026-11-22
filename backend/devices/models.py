"""The merged AED dataset.

A Device is one physical AED as best we know it: location and access from the sources that publish it, plus hardware,
consumables and upkeep, which only owners (operator imports, manual events) can supply. Every value is null until a
source states it. `field_sources` records which source and date each value came from.
"""

from django.db import models

from .address import split_address


class Access(models.TextChoices):
    PUBLIC = "public"
    LIMITED = "limited"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class Readiness(models.TextChoices):
    READY = "ready"
    ATTENTION = "attention"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class OperationalStatus(models.TextChoices):
    OPERATIONAL = "operational"
    OUT_OF_SERVICE = "out_of_service"
    MISSING = "missing"
    DECOMMISSIONED = "decommissioned"
    UNKNOWN = "unknown"


class CoordinateMethod(models.TextChoices):
    GPS = "gps"
    SURVEY = "survey"
    GEOCODED = "geocoded"
    SOURCE = "source"
    UNKNOWN = "unknown"


class Cabinet(models.TextChoices):
    ALARM = "alarm"
    OPEN = "open"
    LOCKED = "locked"
    NONE = "none"
    UNKNOWN = "unknown"


class PadsType(models.TextChoices):
    ADULT = "adult"
    PEDIATRIC = "pediatric"
    UNIVERSAL = "universal"
    UNKNOWN = "unknown"


class BatteryStatus(models.TextChoices):
    OK = "ok"
    LOW = "low"
    REPLACE = "replace"
    UNKNOWN = "unknown"


class Placement(models.TextChoices):
    VEHICLE = "vehicle"
    INSIDE_BUILDING = "inside_building"
    OUTSIDE_ON_BUILDING = "outside_on_building"
    FREESTANDING_OUTDOOR = "freestanding_outdoor"
    UNKNOWN = "unknown"


class Device(models.Model):
    # `geom geography(Point, 4326)` is a generated column added in SQL (migration 0002) from lat/lon, with a GiST
    # index; queries that need it use raw SQL (devices/queries.py), so no GeoDjango/GDAL is needed.
    id = models.CharField(primary_key=True, max_length=40)  # AED-PL-{n}

    # Identity
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    manufacturer = models.CharField(max_length=200, null=True, blank=True)
    model = models.CharField(max_length=200, null=True, blank=True)
    inventory_number = models.CharField(max_length=100, null=True, blank=True)
    manufactured_on = models.DateField(null=True, blank=True)
    installed_on = models.DateField(null=True, blank=True)

    # Location
    lat = models.FloatField()
    lon = models.FloatField()
    coordinate_method = models.CharField(max_length=16, choices=CoordinateMethod.choices, default="unknown")
    coordinate_accuracy_m = models.FloatField(null=True, blank=True)
    address = models.CharField(max_length=300, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    city = models.CharField(max_length=120, null=True, blank=True)
    teryt = models.CharField(max_length=7, null=True, blank=True)
    simc = models.CharField(max_length=7, null=True, blank=True)
    building_name = models.CharField(max_length=300, null=True, blank=True)
    location_detail = models.TextField(null=True, blank=True)
    floor = models.CharField(max_length=20, null=True, blank=True)
    indoor = models.BooleanField(null=True, blank=True)
    placement = models.CharField(max_length=24, choices=Placement.choices, default="unknown")

    # Access
    access = models.CharField(max_length=16, choices=Access.choices, default="unknown")
    access_conditions = models.JSONField(null=True, blank=True, help_text="What a rescuer must do to get the AED")
    opening_hours = models.CharField(max_length=300, null=True, blank=True)
    opening_hours_raw = models.TextField(null=True, blank=True)
    seasonal = models.BooleanField(null=True, blank=True, help_text="Availability changes with the season")
    cabinet = models.CharField(max_length=16, choices=Cabinet.choices, default="unknown")
    is_mobile = models.BooleanField(default=False)
    photo_url = models.URLField(max_length=1000, null=True, blank=True)

    # Pads
    pads_type = models.CharField(max_length=16, choices=PadsType.choices, default="unknown")
    pads_replaced_on = models.DateField(null=True, blank=True)
    pads_expiry_date = models.DateField(null=True, blank=True)
    pediatric_pads_available = models.BooleanField(null=True, blank=True)
    pediatric_mode = models.BooleanField(null=True, blank=True)

    # Battery
    battery_installed_on = models.DateField(null=True, blank=True)
    battery_expiry_date = models.DateField(null=True, blank=True)
    battery_status = models.CharField(max_length=16, choices=BatteryStatus.choices, default="unknown")

    # Upkeep
    last_self_test_at = models.DateTimeField(null=True, blank=True)
    last_self_test_result = models.CharField(max_length=100, null=True, blank=True)
    last_inspection_on = models.DateField(null=True, blank=True)
    next_inspection_due = models.DateField(null=True, blank=True)
    last_used_on = models.DateField(null=True, blank=True)

    # Status
    operational_status = models.CharField(max_length=16, choices=OperationalStatus.choices, default="unknown")
    readiness = models.CharField(max_length=16, choices=Readiness.choices, default="unknown")
    verified_on = models.DateField(null=True, blank=True)
    verification_method = models.CharField(max_length=100, null=True, blank=True)

    # Owner (institutional contact only, never a private person)
    operator_name = models.CharField(max_length=300, null=True, blank=True)
    operator_regon = models.CharField(max_length=14, null=True, blank=True)
    operator_contact = models.CharField(max_length=200, null=True, blank=True)

    # Provenance
    active = models.BooleanField(default=True, help_text="At least one live (not removed) source record")
    merged_into = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    source_count = models.PositiveIntegerField(default=0)
    sources = models.JSONField(default=list, blank=True)
    field_sources = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["readiness"]),
            models.Index(fields=["access"]),
            models.Index(fields=["active"]),
            models.Index(fields=["city"]),
            models.Index(fields=["serial_number"]),
        ]

    def __str__(self):
        return self.id

    # The address in separate parts (dane.gov.pl), derived from `address` on read; see devices/address.py
    @property
    def street_type(self) -> str | None:
        return split_address(self.address)[0]

    @property
    def street(self) -> str | None:
        return split_address(self.address)[1]

    @property
    def house_number(self) -> str | None:
        return split_address(self.address)[2]


class MaintenanceEvent(models.Model):
    class Kind(models.TextChoices):
        PADS_REPLACED = "pads_replaced"
        BATTERY_REPLACED = "battery_replaced"
        INSPECTION = "inspection"
        SELF_TEST = "self_test"
        USED_IN_RESCUE = "used_in_rescue"
        REPAIR = "repair"
        DECOMMISSIONED = "decommissioned"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    date = models.DateField()
    details = models.TextField(blank=True)
    next_due = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=64, help_text="Integration slug, or `manual`")
    reported_by = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["device", "kind", "date", "source"], name="uniq_maintenance_event"),
        ]

    def __str__(self):
        return f"{self.device_id} {self.kind} {self.date}"


class MatchCandidate(models.Model):
    """Two devices from different sources close enough to be the same AED. Never merged without review."""

    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        REJECTED = "rejected"

    device_a = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="+")
    device_b = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="+")
    distance_m = models.FloatField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["distance_m"]
        constraints = [models.UniqueConstraint(fields=["device_a", "device_b"], name="uniq_match_pair")]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.device_a_id} ~ {self.device_b_id} ({self.distance_m:.0f} m)"


class AdminUnit(models.Model):
    """One cadastral unit (jednostka ewidencyjna) from the national boundary register PRG (GUGiK), used to tell which
    municipality and town a device's coordinates fall in (devices/boundaries.py). A unit is a whole urban municipality,
    the town or the rural part of an urban-rural one, a rural municipality, or a district of a big city, so `teryt` is
    always known and `city` only where the unit is a town. `geom geometry(MultiPolygon, 2180)` (PUWG 1992, metres) is
    added in SQL (migration 0004), like Device.geom."""

    code = models.CharField(primary_key=True, max_length=10, help_text="PRG JPT_KOD_JE, e.g. 121508_2")
    name = models.CharField(max_length=200, help_text="PRG JPT_NAZWA_, e.g. 'Zawoja - gmina wiejska'")
    teryt = models.CharField(max_length=7, help_text="TERYT code of the municipality (gmina) the unit belongs to")
    city = models.CharField(max_length=120, null=True, blank=True, help_text="Town name; null for a rural area")
    municipality = models.CharField(max_length=200, help_text="Municipality for display, e.g. 'gmina Zawoja'")
    version = models.DateField(null=True, blank=True, help_text="PRG version date of this unit")

    class Meta:
        indexes = [models.Index(fields=["teryt"])]

    def __str__(self):
        return f"{self.code} {self.name}"


class DeviceReport(models.Model):
    """A report from the public form (/zglos): a missing AED, a wrong position or detail, a broken or locked device, or
    an owner offering data. Only an admin acts on it; reports are never exported or merged into the dataset."""

    class Kind(models.TextChoices):
        MISSING_AED = "missing_aed", "Brakujący AED"
        WRONG_LOCATION = "wrong_location", "Złe położenie"
        WRONG_DETAILS = "wrong_details", "Błędne dane (godziny, dostęp, opis)"
        NOT_WORKING = "not_working", "AED nie działa / brak elektrod"
        LOCKED = "locked", "AED zamknięty / niedostępny"
        HOLDER_UPDATE = "holder_update", "Jestem dysponentem i chcę przekazać dane"

    class Status(models.TextChoices):
        NEW = "new", "Nowe"
        IN_REVIEW = "in_review", "W trakcie"
        RESOLVED = "resolved", "Załatwione"
        REJECTED = "rejected", "Odrzucone"

    kind = models.CharField(max_length=24, choices=Kind.choices)
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    description = models.TextField(max_length=2000)
    contact_email = models.EmailField(blank=True, help_text="Only for follow-up questions; never published")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    admin_note = models.TextField(blank=True)
    ip_hash = models.CharField(max_length=64, blank=True, help_text="Salted hash of the sender's IP, rate limit only")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"#{self.pk} {self.kind} {self.status}"
