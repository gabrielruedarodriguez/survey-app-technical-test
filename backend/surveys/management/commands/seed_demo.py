from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from surveys.models import Membership, Organization, Response, Survey


class Command(BaseCommand):
    help = "Create demo organizations, users, surveys and responses"

    def handle(self, *args, **options):
        user_model = get_user_model()
        northwind, _ = Organization.objects.get_or_create(name="Northwind")
        contoso, _ = Organization.objects.get_or_create(name="Contoso")

        ana, _ = user_model.objects.get_or_create(username="ana")
        ana.set_password("ana123")
        ana.save()
        bob, _ = user_model.objects.get_or_create(username="bob")
        bob.set_password("bob123")
        bob.save()

        Membership.objects.get_or_create(user=ana, organization=northwind)
        Membership.objects.get_or_create(user=bob, organization=contoso)

        survey, _ = Survey.objects.get_or_create(
            external_key="northwind-csat",
            defaults={"organization": northwind, "title": "Customer satisfaction"},
        )
        Survey.objects.get_or_create(
            external_key="contoso-enps",
            defaults={"organization": contoso, "title": "Employee NPS"},
        )

        if not survey.responses.exists():
            for index, days in enumerate([1, 4, 10], start=1):
                Response.objects.create(
                    survey=survey,
                    external_id=f"demo-{index}",
                    status="complete" if index != 2 else "partial",
                    answers={"nps": 10 - index},
                    submitted_at=timezone.now() - timedelta(days=days),
                )

        self.stdout.write(self.style.SUCCESS("Demo data created"))

