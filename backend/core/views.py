from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    ActivityRecord,
    AuditLog,
    DataSource,
    IngestionBatch,
    Organization,
    OrganizationMembership,
)
from core.permissions import HasOrganizationAccess
from core.serializers import (
    ActivityRecordSerializer,
    ActivityUpdateSerializer,
    AuditLogSerializer,
    DashboardStatsSerializer,
    DataSourceSerializer,
    IngestionBatchSerializer,
    OrganizationSerializer,
)
from core.services.ingestion import run_ingestion


def _user_orgs(user):
    return Organization.objects.filter(
        organizationmembership__user=user
    ).distinct()


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orgs = _user_orgs(request.user)
        return Response(
            {
                "username": request.user.username,
                "organizations": OrganizationSerializer(orgs, many=True).data,
            }
        )


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _user_orgs(self.request.user)


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated, HasOrganizationAccess]

    def get_queryset(self):
        return DataSource.objects.filter(
            organization_id=self.kwargs["org_id"],
            is_active=True,
        )


class IngestionView(APIView):
    permission_classes = [IsAuthenticated, HasOrganizationAccess]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, org_id):
        source_id = request.data.get("data_source_id")
        file = request.FILES.get("file")
        if not source_id or not file:
            return Response(
                {"detail": "data_source_id and file are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ds = DataSource.objects.get(id=source_id, organization_id=org_id)
        except DataSource.DoesNotExist:
            return Response({"detail": "Data source not found"}, status=404)

        content = file.read()
        if len(content) > 10 * 1024 * 1024:
            return Response({"detail": "File too large (max 10MB)"}, status=400)

        batch = run_ingestion(
            organization=ds.organization,
            data_source=ds,
            content=content,
            filename=file.name,
            user=request.user,
        )
        return Response(
            IngestionBatchSerializer(batch).data,
            status=status.HTTP_201_CREATED,
        )


class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityRecordSerializer
    permission_classes = [IsAuthenticated, HasOrganizationAccess]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = ActivityRecord.objects.filter(
            organization_id=self.kwargs["org_id"]
        ).select_related("data_source", "batch")
        status_filter = self.request.query_params.get("status")
        source = self.request.query_params.get("source")
        scope = self.request.query_params.get("scope")
        if status_filter:
            qs = qs.filter(review_status=status_filter)
        if source:
            qs = qs.filter(data_source__source_type=source)
        if scope:
            qs = qs.filter(scope=scope)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return ActivityUpdateSerializer
        return ActivityRecordSerializer

    def partial_update(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.review_status == ActivityRecord.ReviewStatus.LOCKED:
            return Response({"detail": "Record is locked for audit"}, status=403)

        before = ActivityRecordSerializer(activity).data
        serializer = ActivityUpdateSerializer(
            activity, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(is_edited=True, version=activity.version + 1)

        AuditLog.objects.create(
            organization=activity.organization,
            activity=activity,
            actor=request.user,
            action=AuditLog.Action.EDIT,
            before_state=before,
            after_state=ActivityRecordSerializer(activity).data,
        )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, org_id=None, pk=None):
        activity = self.get_object()
        if activity.review_status == ActivityRecord.ReviewStatus.LOCKED:
            return Response({"detail": "Already locked"}, status=400)
        if activity.review_status == ActivityRecord.ReviewStatus.FAILED:
            return Response(
                {"detail": "Cannot approve failed records — fix or re-ingest"},
                status=400,
            )

        before = activity.review_status
        activity.review_status = ActivityRecord.ReviewStatus.APPROVED
        activity.reviewed_by = request.user
        activity.reviewed_at = timezone.now()
        activity.save()

        AuditLog.objects.create(
            organization=activity.organization,
            activity=activity,
            actor=request.user,
            action=AuditLog.Action.APPROVE,
            before_state={"review_status": before},
            after_state={"review_status": activity.review_status},
        )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, org_id=None, pk=None):
        activity = self.get_object()
        if activity.review_status != ActivityRecord.ReviewStatus.APPROVED:
            return Response(
                {"detail": "Only approved records can be locked"},
                status=400,
            )
        activity.review_status = ActivityRecord.ReviewStatus.LOCKED
        activity.save()
        AuditLog.objects.create(
            organization=activity.organization,
            activity=activity,
            actor=request.user,
            action=AuditLog.Action.LOCK,
            after_state={"review_status": "locked"},
        )
        return Response(ActivityRecordSerializer(activity).data)


class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer
    permission_classes = [IsAuthenticated, HasOrganizationAccess]

    def get_queryset(self):
        return IngestionBatch.objects.filter(
            organization_id=self.kwargs["org_id"]
        ).select_related("data_source").order_by("-created_at")[:50]


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, HasOrganizationAccess]

    def get(self, request, org_id):
        qs = ActivityRecord.objects.filter(organization_id=org_id)
        counts = qs.values("review_status").annotate(c=Count("id"))
        by_status = {row["review_status"]: row["c"] for row in counts}
        by_source = {
            row["data_source__source_type"]: row["c"]
            for row in qs.values("data_source__source_type").annotate(c=Count("id"))
        }
        data = {
            "total": qs.count(),
            "pending": by_status.get("pending", 0),
            "suspicious": by_status.get("suspicious", 0),
            "failed": by_status.get("failed", 0),
            "approved": by_status.get("approved", 0),
            "locked": by_status.get("locked", 0),
            "by_source": by_source,
        }
        return Response(DashboardStatsSerializer(data).data)


class AuditLogView(APIView):
    permission_classes = [IsAuthenticated, HasOrganizationAccess]

    def get(self, request, org_id):
        activity_id = request.query_params.get("activity_id")
        qs = AuditLog.objects.filter(organization_id=org_id)
        if activity_id:
            qs = qs.filter(activity_id=activity_id)
        qs = qs.select_related("actor")[:100]
        return Response(AuditLogSerializer(qs, many=True).data)
