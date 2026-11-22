from django.contrib import admin

from .models import Device, MaintenanceEvent, MatchCandidate


class EventInline(admin.TabularInline):
    model = MaintenanceEvent
    extra = 0


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "building_name", "city", "access", "readiness", "source_count", "active"]
    list_filter = ["readiness", "access", "active"]
    search_fields = ["id", "building_name", "address", "city", "serial_number"]
    inlines = [EventInline]
    raw_id_fields = ["merged_into"]


@admin.register(MatchCandidate)
class MatchCandidateAdmin(admin.ModelAdmin):
    list_display = ["id", "device_a", "device_b", "distance_m", "status"]
    list_filter = ["status"]
    raw_id_fields = ["device_a", "device_b"]
