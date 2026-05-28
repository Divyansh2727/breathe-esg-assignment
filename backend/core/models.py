from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Tenant boundary — all activity data is scoped to one org."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[
            ("analyst", "Analyst"),
            ("admin", "Admin"),
        ],
        default="analyst",
    )

    class Meta:
        unique_together = ("user", "organization")


class DataSource(models.Model):
    """Configured connector per org (SAP file, utility portal CSV, travel export)."""

    class SourceType(models.TextChoices):
        SAP = "sap", "SAP (fuel & procurement)"
        UTILITY = "utility", "Utility portal (electricity)"
        TRAVEL = "travel", "Corporate travel (Concur-style)"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="data_sources"
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    name = models.CharField(max_length=120)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "source_type", "name")

    def __str__(self):
        return f"{self.organization.slug}:{self.source_type}"


class PlantLookup(models.Model):
    """Maps opaque SAP plant codes to human-readable sites."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    plant_code = models.CharField(max_length=10)
    site_name = models.CharField(max_length=200)
    country = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("organization", "plant_code")


class IngestionBatch(models.Model):
    """One upload or API pull attempt."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="batches"
    )
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    row_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class RawRecord(models.Model):
    """Immutable source payload + parse outcome for lineage."""

    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.CASCADE, related_name="raw_records"
    )
    line_number = models.PositiveIntegerField()
    raw_payload = models.JSONField()
    parse_status = models.CharField(
        max_length=20,
        choices=[
            ("ok", "Parsed OK"),
            ("error", "Parse error"),
            ("skipped", "Skipped"),
        ],
        default="ok",
    )
    parse_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ActivityRecord(models.Model):
    """
    Normalized activity row — the unit analysts review before audit lock.
    Quantity is stored in canonical units (L, kWh, km, nights).
    """

    class Scope(models.TextChoices):
        SCOPE_1 = "1", "Scope 1"
        SCOPE_2 = "2", "Scope 2"
        SCOPE_3 = "3", "Scope 3"

    class Category(models.TextChoices):
        STATIONARY_COMBUSTION = "stationary_combustion", "Stationary combustion"
        MOBILE_COMBUSTION = "mobile_combustion", "Mobile combustion"
        PURCHASED_ELECTRICITY = "purchased_electricity", "Purchased electricity"
        PURCHASED_GOODS = "purchased_goods", "Purchased goods"
        BUSINESS_TRAVEL = "business_travel", "Business travel"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending review"
        SUSPICIOUS = "suspicious", "Flagged suspicious"
        FAILED = "failed", "Failed validation"
        APPROVED = "approved", "Approved"
        LOCKED = "locked", "Locked for audit"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="activities"
    )
    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.PROTECT, related_name="activities"
    )
    raw_record = models.OneToOneField(
        RawRecord,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activity",
    )
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT)

    scope = models.CharField(max_length=1, choices=Scope.choices)
    category = models.CharField(max_length=40, choices=Category.choices)
    subcategory = models.CharField(max_length=80, blank=True)

    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    facility_code = models.CharField(max_length=50, blank=True)
    facility_name = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=500, blank=True)

    quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    original_quantity = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    original_unit = models.CharField(max_length=20, blank=True)

    source_reference = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    suspicion_reasons = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_activities",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    analyst_notes = models.TextField(blank=True)

    is_edited = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "review_status"]),
            models.Index(fields=["organization", "scope", "category"]),
            models.Index(fields=["batch"]),
        ]


class AuditLog(models.Model):
    """Append-only trail for compliance."""

    class Action(models.TextChoices):
        INGEST = "ingest", "Ingestion"
        PARSE_ERROR = "parse_error", "Parse error"
        FLAG = "flag", "Flag suspicious"
        EDIT = "edit", "Analyst edit"
        APPROVE = "approve", "Approve"
        LOCK = "lock", "Lock for audit"
        REJECT = "reject", "Reject"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    activity = models.ForeignKey(
        ActivityRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    batch = models.ForeignKey(
        IngestionBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
