from django.db import migrations
from django.db.models import Count, Min


def remove_duplicate_responses(apps, schema_editor):
    Response = apps.get_model("surveys", "Response")
    duplicates = (
        Response.objects.order_by()
        .values("survey_id", "external_id")
        .annotate(first_id=Min("id"), total=Count("id"))
        .filter(total__gt=1)
    )
    for duplicate in duplicates:
        Response.objects.filter(
            survey_id=duplicate["survey_id"], external_id=duplicate["external_id"]
        ).exclude(id=duplicate["first_id"]).delete()


class Migration(migrations.Migration):
    dependencies = [("surveys", "0001_initial")]

    operations = [
        migrations.RunPython(remove_duplicate_responses, migrations.RunPython.noop),
    ]
