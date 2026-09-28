from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Membership, Organization, Response, Survey
from .services import response_get_or_create


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


class ResponseWebhookIdempotencyTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Northwind")
        self.survey = Survey.objects.create(
            organization=self.organization,
            title="Customer satisfaction",
            external_key="northwind-csat",
        )
        self.client = APIClient()
        self.client.credentials(HTTP_X_WEBHOOK_TOKEN=settings.WEBHOOK_TOKEN)

    def deliver(self, **overrides):
        payload = {
            "survey_key": self.survey.external_key,
            "event_id": "evt-100",
            "status": "complete",
            "answers": {"nps": 9},
            "submitted_at": "2026-09-27T10:00:00Z",
            **overrides,
        }
        return self.client.post("/api/webhooks/responses/", payload, format="json")

    def test_first_delivery_creates_response(self):
        response = self.deliver()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Response.objects.count(), 1)

    def test_repeated_delivery_returns_stored_response_without_duplicating(self):
        first = self.deliver()
        retry = self.deliver()

        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.data, first.data)
        self.assertEqual(Response.objects.count(), 1)

    def test_retry_with_different_payload_keeps_first_write(self):
        self.deliver(status="partial", answers={"nps": 5})
        retry = self.deliver(status="complete", answers={"nps": 9})

        self.assertEqual(retry.status_code, 200)
        stored = Response.objects.get()
        self.assertEqual(stored.status, "partial")
        self.assertEqual(stored.answers, {"nps": 5})

    def test_same_event_id_on_another_survey_creates_separate_response(self):
        contoso = Organization.objects.create(name="Contoso")
        other_survey = Survey.objects.create(
            organization=contoso, title="Employee NPS", external_key="contoso-enps"
        )
        self.deliver()

        response = self.deliver(survey_key=other_survey.external_key)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Response.objects.count(), 2)


class ResponseGetOrCreateTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Northwind")
        self.survey = Survey.objects.create(
            organization=organization,
            title="Customer satisfaction",
            external_key="northwind-csat",
        )

    def test_losing_a_concurrent_insert_returns_the_stored_response(self):
        # Row committed by the concurrent delivery that won the race.
        winner = Response.objects.create(
            survey=self.survey,
            external_id="evt-100",
            status="complete",
            answers={"nps": 9},
            submitted_at=timezone.now(),
        )

        response, created = response_get_or_create(
            survey=self.survey,
            event_id="evt-100",
            status="complete",
            answers={"nps": 9},
            submitted_at=timezone.now(),
        )

        self.assertFalse(created)
        self.assertEqual(response.pk, winner.pk)
        self.assertEqual(Response.objects.count(), 1)


class RemoveDuplicateResponsesMigrationTests(TransactionTestCase):
    before = [("surveys", "0001_initial")]
    after = [("surveys", "0003_response_unique_event")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old_apps = executor.loader.project_state(self.before).apps
        organization = old_apps.get_model("surveys", "Organization").objects.create(
            name="Northwind"
        )
        survey = old_apps.get_model("surveys", "Survey").objects.create(
            organization=organization, title="Customer satisfaction", external_key="csat"
        )
        old_response = old_apps.get_model("surveys", "Response")
        self.first_response_ids = {}
        for event_id in ["evt-1", "evt-1", "evt-1", "evt-2"]:
            response = old_response.objects.create(
                survey=survey,
                external_id=event_id,
                status="complete",
                answers={},
                submitted_at=timezone.now(),
            )
            self.first_response_ids.setdefault(event_id, response.pk)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_keeps_only_the_first_response_of_each_event(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        new_apps = executor.loader.project_state(self.after).apps
        remaining = new_apps.get_model("surveys", "Response").objects.values_list(
            "external_id", "pk"
        )

        self.assertEqual(sorted(remaining), sorted(self.first_response_ids.items()))
