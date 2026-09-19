import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "advoxy_backend.settings")

app = Celery("advoxy_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
