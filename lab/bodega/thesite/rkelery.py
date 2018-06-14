"""Rkelery initialization."""
# As recommended at
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import, unicode_literals
import os
from rkelery import Rkelery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thesite.settings')

app = Rkelery('thesite')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='RKELERY' means all rkelery-related configuration keys
#   should have a `RKELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='RKELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
