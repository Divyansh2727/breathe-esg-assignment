from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import (
    ActivityRecord,
    AuditLog,
    DataSource,
    IngestionBatch,
    Organization,
    PlantLookup,
    RawRecord,
)
from core.parsers import parse_sap_file, parse_travel_file, parse_utility_file


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _plant_lookup(org: Organization) -> dict[str, str]:
    return {
        p.plant_code: p.site_name
        for p in PlantLookup.objects.filter(organization=org)
    }


def _determine_review_status(parsed_row: dict, activity: dict | None) -> str:
    if parsed_row["parse_status"] == "error":
        return ActivityRecord.ReviewStatus.FAILED
    if parsed_row["parse_status"] == "skipped" or activity is None:
        return ActivityRecord.ReviewStatus.FAILED
    if activity.get("validation_errors"):
        return ActivityRecord.ReviewStatus.FAILED
    if activity.get("suspicion_reasons"):
        return ActivityRecord.ReviewStatus.SUSPICIOUS
    return ActivityRecord.ReviewStatus.PENDING


@transaction.atomic
def run_ingestion(
    *,
    organization: Organization,
    data_source: DataSource,
    content: bytes,
    filename: str,
    user,
) -> IngestionBatch:
    batch = IngestionBatch.objects.create(
        organization=organization,
        data_source=data_source,
        uploaded_by=user,
        filename=filename,
        status=IngestionBatch.Status.PROCESSING,
    )

    try:
        if data_source.source_type == DataSource.SourceType.SAP:
            parsed = parse_sap_file(content, _plant_lookup(organization))
        elif data_source.source_type == DataSource.SourceType.UTILITY:
            parsed = parse_utility_file(content)
        elif data_source.source_type == DataSource.SourceType.TRAVEL:
            parsed = parse_travel_file(content)
        else:
            raise ValueError(f"Unknown source type: {data_source.source_type}")
    except Exception as exc:
        batch.status = IngestionBatch.Status.FAILED
        batch.summary = {"error": str(exc)}
        batch.completed_at = timezone.now()
        batch.save()
        AuditLog.objects.create(
            organization=organization,
            batch=batch,
            actor=user,
            action=AuditLog.Action.PARSE_ERROR,
            note=str(exc),
        )
        return batch

    success = error = 0
    for row in parsed:
        raw = RawRecord.objects.create(
            batch=batch,
            line_number=row["line_number"],
            raw_payload=row["raw_payload"],
            parse_status=row["parse_status"],
            parse_errors=row.get("parse_errors", []),
        )

        activity_data = row.get("activity")
        review_status = _determine_review_status(row, activity_data)

        if activity_data:
            ActivityRecord.objects.create(
                organization=organization,
                batch=batch,
                raw_record=raw,
                data_source=data_source,
                scope=activity_data["scope"],
                category=activity_data["category"],
                subcategory=activity_data.get("subcategory", ""),
                activity_date=_to_date(activity_data.get("activity_date")),
                period_start=_to_date(activity_data.get("period_start")),
                period_end=_to_date(activity_data.get("period_end")),
                facility_code=activity_data.get("facility_code", ""),
                facility_name=activity_data.get("facility_name", ""),
                description=activity_data.get("description", ""),
                quantity=(
                    Decimal(activity_data["quantity"])
                    if activity_data.get("quantity")
                    else None
                ),
                unit=activity_data.get("unit", ""),
                original_quantity=(
                    Decimal(activity_data["original_quantity"])
                    if activity_data.get("original_quantity")
                    else None
                ),
                original_unit=activity_data.get("original_unit", ""),
                source_reference=activity_data.get("source_reference", ""),
                metadata=activity_data.get("metadata", {}),
                review_status=review_status,
                suspicion_reasons=activity_data.get("suspicion_reasons", []),
                validation_errors=activity_data.get("validation_errors", [])
                or row.get("parse_errors", []),
            )
            if review_status == ActivityRecord.ReviewStatus.FAILED:
                error += 1
            else:
                success += 1
        else:
            error += 1

    batch.row_count = len(parsed)
    batch.success_count = success
    batch.error_count = error
    batch.status = IngestionBatch.Status.COMPLETED
    batch.summary = {
        "parsed": len(parsed),
        "activities_created": success + sum(
            1 for r in parsed if r.get("activity") and _determine_review_status(r, r["activity"]) == ActivityRecord.ReviewStatus.FAILED
        ),
    }
    batch.completed_at = timezone.now()
    batch.save()

    AuditLog.objects.create(
        organization=organization,
        batch=batch,
        actor=user,
        action=AuditLog.Action.INGEST,
        after_state={
            "filename": filename,
            "row_count": batch.row_count,
            "success_count": batch.success_count,
            "error_count": batch.error_count,
        },
    )
    return batch
