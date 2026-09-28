from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="unique_membership"
            )
        ]


class Survey(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="surveys"
    )
    title = models.CharField(max_length=200)
    external_key = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.title


class Response(models.Model):
    STATUS_CHOICES = [("partial", "Partial"), ("complete", "Complete")]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="responses"
    )
    external_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "external_id"], name="unique_response_event"
            )
        ]

