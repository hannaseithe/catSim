from uuid import uuid4
import uuid
from django.conf import settings
from django.db import migrations, models


def generateUUID(apps, schema_editor):
    SimulationRun = apps.get_model("cats", "SimulationRun")
    for run in SimulationRun.objects.filter(uuid__isnull=True):
        run.uuid = uuid4()
        run.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("cats", "0005_alter_simulationrun_user"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="simulationrun",
            name="uuid",
            field=models.UUIDField(
                null=True, unique=True, editable=False
            ),
        ),
        migrations.RunPython(generateUUID),
        migrations.AlterField(
            model_name="simulationrun",
            name="uuid",
            field= models.UUIDField(unique=True, editable=False, default=uuid.uuid4),
        )
    ]
