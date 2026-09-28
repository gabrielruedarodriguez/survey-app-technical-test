from rest_framework import permissions

from .selectors import organizations_for_user


class OrganizationScopedMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        organizations = organizations_for_user(self.request.user)
        return super().get_queryset().filter(organization__in=organizations)
