"""RKelery app config."""
from django.apps import AppConfig


class RkeleryAppConfig(AppConfig):

    name = 'rkelery'
    verbose_name = 'RKelery integration'

    # In order to separate our custom signals from our models.py
    # file, we need to import signals from this ready function
    # or else we will create circular dependencies since some of the
    # signals depends on the models.
    def ready(self):

        from . import signals  # noqa
