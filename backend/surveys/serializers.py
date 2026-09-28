from rest_framework import serializers

from .models import Response


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ["id", "external_id", "status", "answers", "submitted_at"]


class WebhookSerializer(serializers.Serializer):
    survey_key = serializers.CharField()
    event_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["partial", "complete"])
    answers = serializers.JSONField()
    submitted_at = serializers.DateTimeField()

