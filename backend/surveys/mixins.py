from rest_framework import permissions

from .selectors import organization_list


class OrganizationScopedMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        organizations = organization_list(user=self.request.user)
        return super().get_queryset().filter(organization__in=organizations)
