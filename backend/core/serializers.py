from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.models import (
    ActivityRecord,
    AuditLog,
    DataSource,
    IngestionBatch,
    Organization,
)

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug")


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ("id", "source_type", "name", "is_active", "created_at")


class IngestionBatchSerializer(serializers.ModelSerializer):
    data_source = DataSourceSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = (
            "id",
            "data_source",
            "filename",
            "status",
            "row_count",
            "success_count",
            "error_count",
            "summary",
            "created_at",
            "completed_at",
        )


class ActivityRecordSerializer(serializers.ModelSerializer):
    data_source_type = serializers.CharField(
        source="data_source.source_type", read_only=True
    )
    batch_filename = serializers.CharField(source="batch.filename", read_only=True)

    class Meta:
        model = ActivityRecord
        fields = (
            "id",
            "scope",
            "category",
            "subcategory",
            "activity_date",
            "period_start",
            "period_end",
            "facility_code",
            "facility_name",
            "description",
            "quantity",
            "unit",
            "original_quantity",
            "original_unit",
            "source_reference",
            "metadata",
            "review_status",
            "suspicion_reasons",
            "validation_errors",
            "is_edited",
            "version",
            "analyst_notes",
            "reviewed_at",
            "data_source_type",
            "batch_filename",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "scope",
            "category",
            "data_source_type",
            "batch_filename",
            "is_edited",
            "version",
            "created_at",
            "updated_at",
        )


class ActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = (
            "quantity",
            "unit",
            "description",
            "facility_name",
            "analyst_notes",
            "period_start",
            "period_end",
        )


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "actor_username",
            "before_state",
            "after_state",
            "note",
            "created_at",
        )


class DashboardStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    suspicious = serializers.IntegerField()
    failed = serializers.IntegerField()
    approved = serializers.IntegerField()
    locked = serializers.IntegerField()
    by_source = serializers.DictField()
