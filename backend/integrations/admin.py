from django.contrib import admin, messages

from .engine import SyncRefused, queue_sync
from .models import Integration, SourceRecord, SyncRun


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = [
        "slug",
        "name",
        "connector",
        "enabled",
        "periodic_enabled",
        "sync_interval_hours",
        "priority",
        "historical_completed_at",
        "last_success_at",
        "next_run_at",
    ]
    # Priority and interval are declared on the connector class: shown, never edited
    list_editable = ["enabled", "periodic_enabled"]
    readonly_fields = ["priority", "sync_interval_hours"]
    actions = ["sync_now", "dry_run"]

    def _queue(self, request, queryset, **kwargs):
        for integration in queryset:
            try:
                queue_sync(integration, SyncRun.Kind.PERIODIC, SyncRun.Trigger.MANUAL, **kwargs)
            except SyncRefused as exc:
                self.message_user(request, str(exc), messages.WARNING)

    @admin.action(description="Synchronizuj teraz")
    def sync_now(self, request, queryset):
        self._queue(request, queryset)

    @admin.action(description="Test (dry run)")
    def dry_run(self, request, queryset):
        self._queue(request, queryset, dry_run=True)


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "integration",
        "kind",
        "trigger",
        "status",
        "dry_run",
        "created_at",
        "fetched",
        "created",
        "updated",
        "removed",
        "invalid",
    ]
    list_filter = ["status", "kind", "integration"]


@admin.register(SourceRecord)
class SourceRecordAdmin(admin.ModelAdmin):
    list_display = ["source_record_id", "integration", "is_valid", "device", "last_seen", "removed_at"]
    list_filter = ["integration", "is_valid"]
    search_fields = ["source_record_id"]
    raw_id_fields = ["device", "last_run"]
