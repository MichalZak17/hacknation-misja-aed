"""Sources of AED data and their syncs.

An Integration is one database row per source; its `connector` names the code (integrations/connectors/) that fetches
and parses it. Every run is a SyncRun. Every record a source publishes is a SourceRecord: the provider's own
observation, kept with its raw payload and linked to the merged Device it describes (devices/).
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone


def default_interval():
    # Referenced by migration 0001. The real value comes from the connector class (see Integration.save()).
    return 24


class Integration(models.Model):
    slug = models.SlugField(unique=True, max_length=64)
    name = models.CharField(max_length=200)
    connector = models.CharField(max_length=64, help_text="Key in integrations.connectors.REGISTRY")
    description = models.TextField(blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(max_length=1000, blank=True, help_text="The file or endpoint that is fetched")
    homepage_url = models.URLField(max_length=1000, blank=True, help_text="Catalogue or publisher page")
    license = models.CharField(max_length=100, blank=True)
    license_url = models.URLField(max_length=1000, blank=True)
    attribution = models.CharField(max_length=300, blank=True)
    format = models.CharField(max_length=32, blank=True)
    config = models.JSONField(default=dict, blank=True, help_text="Connector options (bounds, url overrides, …)")

    enabled = models.BooleanField(default=True)
    periodic_enabled = models.BooleanField(default=True)
    # Declared on the connector class and copied here on every save and deploy (`seed_integrations`), never edited:
    # kept as columns so the merge, the scheduler and listings can sort by them in SQL
    sync_interval_hours = models.PositiveIntegerField(default=default_interval)
    # Higher wins when merged sources disagree on a field (operator data > city data > OSM)
    priority = models.IntegerField(default=50)

    historical_completed_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.apply_connector_settings()
        super().save(*args, **kwargs)

    def apply_connector_settings(self) -> bool:
        """Copy priority and interval from the connector class. True when either changed; a new interval moves the
        next scheduled run."""
        from .connectors import REGISTRY

        connector = REGISTRY.get(self.connector)
        if connector is None:
            return False
        changed = (self.priority, self.sync_interval_hours) != (connector.priority, connector.sync_interval_hours)
        interval_changed = self.sync_interval_hours != connector.sync_interval_hours
        self.priority, self.sync_interval_hours = connector.priority, connector.sync_interval_hours
        if interval_changed and self.pk and self.historical_completed_at:
            self.schedule_next(self.last_success_at or timezone.now())
        return changed

    def schedule_next(self, now=None):
        now = now or timezone.now()
        self.next_run_at = now + timedelta(hours=self.sync_interval_hours) if self.periodic_enabled else None


class SyncRun(models.Model):
    class Kind(models.TextChoices):
        HISTORICAL = "historical"
        PERIODIC = "periodic"

    class Trigger(models.TextChoices):
        SEED = "seed"
        SCHEDULE = "schedule"
        MANUAL = "manual"

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="runs")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    trigger = models.CharField(max_length=16, choices=Trigger.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    dry_run = models.BooleanField(default=False)
    force = models.BooleanField(default=False)
    # Ask the LLM again for every record with free text, ignoring cached answers (the admin's AI classification view)
    reextract = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    fetched = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    unchanged = models.PositiveIntegerField(default=0)
    removed = models.PositiveIntegerField(default=0)
    invalid = models.PositiveIntegerField(default=0)

    error = models.TextField(blank=True)
    snapshot_path = models.CharField(max_length=500, blank=True)
    snapshot_sha256 = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["integration", "-created_at"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.integration.slug} {self.kind} #{self.pk} ({self.status})"

    @property
    def duration_ms(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() * 1000)
        return None


class SourceRecord(models.Model):
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="records")
    source_record_id = models.CharField(max_length=200)
    lat = models.FloatField(null=True)
    lon = models.FloatField(null=True)
    is_valid = models.BooleanField(default=True)
    issues = models.JSONField(default=list, blank=True)
    # Normalised fields (the Device vocabulary) and the provider's payload as published
    data = models.JSONField(default=dict, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    content_hash = models.CharField(max_length=64)

    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    removed_at = models.DateTimeField(null=True, blank=True)
    last_run = models.ForeignKey(SyncRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    device = models.ForeignKey(
        "devices.Device", null=True, blank=True, on_delete=models.SET_NULL, related_name="records"
    )

    # Facts a local LLM read from this record's free text (integrations/enrichment), in the Device vocabulary. Kept
    # apart from `data`: the merge uses them only where no source states the field. `inferred_key` identifies the
    # input + prompt + model that produced them ('' = never extracted, or nothing to extract).
    inferred = models.JSONField(default=dict, blank=True)
    inferred_key = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["integration", "source_record_id"], name="uniq_source_record"),
        ]
        indexes = [models.Index(fields=["integration", "is_valid"]), models.Index(fields=["device"])]

    def __str__(self):
        return f"{self.integration.slug}:{self.source_record_id}"


class TextExtraction(models.Model):
    """Cache of LLM answers, one per distinct (prompt version, model, input). Identical texts across records, sources
    and syncs are extracted once; a failed call is stored with its error and retried on the next sync."""

    key = models.CharField(primary_key=True, max_length=64)
    model = models.CharField(max_length=200)
    prompt_version = models.CharField(max_length=40)
    input = models.JSONField()
    output = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.prompt_version}/{self.model} {self.key[:12]}"
