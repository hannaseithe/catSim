from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_placeholder_user_and_assign(apps, schema_editor):
    User = apps.get_model('accounts', 'CustomUser')
    SimulationRun = apps.get_model('cats', 'SimulationRun')

    placeholder_email = "miaumator@example.com"
    placeholder_user, created = User.objects.get_or_create(
        email=placeholder_email,
        defaults={
            "password": make_password("changeme123"),
            "is_staff": False,
            "is_superuser": False,
        },
    )
    SimulationRun.objects.filter(user__isnull=True).update(user=placeholder_user)


class Migration(migrations.Migration):

    dependencies = [
        ('cats', '0003_rename_error_messages_simulationrun_error_message_and_more'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_placeholder_user_and_assign)
    ]
