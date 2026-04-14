# project/celery.py
import os
from celery import Celery
from decouple import config
# Set the default Django settings module for the 'celery' program.
IS_LIVE = config('IS_LIVE', default=False, cast=bool)
if IS_LIVE:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.development')

app = Celery('Config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
