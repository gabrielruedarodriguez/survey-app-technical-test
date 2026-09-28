from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet

from .models import Organization, Response, Survey


def organization_list(*, user: AbstractBaseUser) -> QuerySet[Organization]:
    return Organization.objects.filter(memberships__user=user)


def response_list(*, survey: Survey) -> QuerySet[Response]:
    return Response.objects.filter(survey=survey)
