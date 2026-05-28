from django.contrib import admin

from core.models import (
    ActivityRecord,
    AuditLog,
    DataSource,
    IngestionBatch,
    Organization,
    PlantLookup,
    RawRecord,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")


@admin.register(ActivityRecord)
class ActivityRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "scope",
        "category",
        "review_status",
        "quantity",
        "unit",
    )
    list_filter = ("review_status", "scope", "category")


admin.site.register(DataSource)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)
admin.site.register(PlantLookup)
admin.site.register(AuditLog)
