from django.db.models import QuerySet

from .models import Organization


def organizations_for_user(user) -> QuerySet[Organization]:
    return Organization.objects.filter(memberships__user=user)
