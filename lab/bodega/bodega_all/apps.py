"""Bodega all app config."""
from __future__ import unicode_literals

from django.apps import AppConfig


class BodegaAllAppConfig(AppConfig):
    name = 'bodega_all'

    def ready(self):
        from . import signals  # noqa

        # Import the tasks so they'll be registered throughout the app. This
        # is slightly hacky, not sure if there's a better way.
        from . import tasks  # noqa
