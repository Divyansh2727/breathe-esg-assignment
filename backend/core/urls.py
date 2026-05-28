from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    ActivityViewSet,
    AuditLogView,
    BatchViewSet,
    DashboardView,
    DataSourceViewSet,
    IngestionView,
    MeView,
    OrganizationViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")

org_router = DefaultRouter()
org_router.register("sources", DataSourceViewSet, basename="source")
org_router.register("activities", ActivityViewSet, basename="activity")
org_router.register("batches", BatchViewSet, basename="batch")

urlpatterns = [
    path("me/", MeView.as_view()),
    path("organizations/<int:org_id>/ingest/", IngestionView.as_view()),
    path("organizations/<int:org_id>/dashboard/", DashboardView.as_view()),
    path("organizations/<int:org_id>/audit/", AuditLogView.as_view()),
    path("organizations/<int:org_id>/", include(org_router.urls)),
    path("", include(router.urls)),
]
