from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Membership, Organization, Response, Survey


class SurveyApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Northwind")
        self.user = get_user_model().objects.create_user("ana", password="ana123")
        Membership.objects.create(user=self.user, organization=self.organization)
        self.survey = Survey.objects.create(
            organization=self.organization,
            title="Customer satisfaction",
            external_key="northwind-csat",
        )
        Response.objects.create(
            survey=self.survey,
            external_id="evt-001",
            status="complete",
            answers={"nps": 9},
            submitted_at=timezone.now() - timedelta(days=1),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authorized_user_can_list_results(self):
        response = self.client.get(f"/api/surveys/{self.survey.id}/results/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_webhook_rejects_invalid_token(self):
        response = self.client.post(
            "/api/webhooks/responses/",
            {
                "survey_key": self.survey.external_key,
                "event_id": "evt-002",
                "status": "complete",
                "answers": {"nps": 8},
                "submitted_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)


class SurveyResultsIsolationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.northwind = Organization.objects.create(name="Northwind")
        self.contoso = Organization.objects.create(name="Contoso")
        self.ana = user_model.objects.create_user("ana", password="ana123")
        self.bob = user_model.objects.create_user("bob", password="bob123")
        Membership.objects.create(user=self.ana, organization=self.northwind)
        Membership.objects.create(user=self.bob, organization=self.contoso)
        self.northwind_survey = Survey.objects.create(
            organization=self.northwind,
            title="Customer satisfaction",
            external_key="northwind-csat",
        )
        self.contoso_survey = Survey.objects.create(
            organization=self.contoso,
            title="Employee NPS",
            external_key="contoso-enps",
        )
        self.client = APIClient()

    def results_url(self, survey_id):
        return f"/api/surveys/{survey_id}/results/"

    def test_user_cannot_read_survey_from_another_organization(self):
        self.client.force_authenticate(self.bob)

        response = self.client.get(self.results_url(self.northwind_survey.id))

        self.assertEqual(response.status_code, 404)

    def test_foreign_survey_is_indistinguishable_from_missing_survey(self):
        self.client.force_authenticate(self.bob)

        foreign = self.client.get(self.results_url(self.northwind_survey.id))
        missing = self.client.get(self.results_url(999999))

        self.assertEqual(foreign.status_code, missing.status_code)
        self.assertEqual(foreign.data, missing.data)

    def test_user_without_membership_cannot_read_any_survey(self):
        outsider = get_user_model().objects.create_user("eve", password="eve123")
        self.client.force_authenticate(outsider)

        response = self.client.get(self.results_url(self.northwind_survey.id))

        self.assertEqual(response.status_code, 404)

    def test_member_of_several_organizations_can_read_each_survey(self):
        Membership.objects.create(user=self.ana, organization=self.contoso)
        self.client.force_authenticate(self.ana)

        for survey in (self.northwind_survey, self.contoso_survey):
            with self.subTest(survey=survey.title):
                response = self.client.get(self.results_url(survey.id))

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["survey"]["id"], survey.id)

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(self.results_url(self.northwind_survey.id))

        self.assertEqual(response.status_code, 401)
