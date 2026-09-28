from datetime import datetime

from django.db import IntegrityError, transaction

from .models import Response, Survey


def response_get_or_create(
    *,
    survey: Survey,
    event_id: str,
    status: str,
    answers: dict,
    submitted_at: datetime,
) -> tuple[Response, bool]:
    try:
        with transaction.atomic():
            response = Response.objects.create(
                survey=survey,
                external_id=event_id,
                status=status,
                answers=answers,
                submitted_at=submitted_at,
            )
    except IntegrityError:
        # Another delivery of the same event already stored it.
        return Response.objects.get(survey=survey, external_id=event_id), False

    return response, True
