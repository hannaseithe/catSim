
import os
from celery import Celery

# Tell Celery where Django settings live
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_project.settings")

# Create the Celery app instance
app = Celery("django_project")

# Load configuration from Django settings, using CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all INSTALLED_APPS
app.autodiscover_tasks()