from rest_framework.permissions import BasePermission

from core.models import OrganizationMembership


class HasOrganizationAccess(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get("org_id") or request.query_params.get("org")
        if not org_id:
            return False
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization_id=org_id,
        ).exists()
