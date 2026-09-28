from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet

from .models import Organization


def organization_list(*, user: AbstractBaseUser) -> QuerySet[Organization]:
    return Organization.objects.filter(memberships__user=user)
