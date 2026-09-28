from django.urls import path

from .views import ResponseWebhookView, SurveyResultsView

urlpatterns = [
    path("surveys/<int:survey_id>/results/", SurveyResultsView.as_view()),
    path("webhooks/responses/", ResponseWebhookView.as_view()),
]

