"""Celery application instance for the project."""

import os

from celery import Celery

os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"

app = Celery('julizen')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga explícita de tareas para asegurar el registro
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
