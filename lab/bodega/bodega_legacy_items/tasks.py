"""Bodega legacy items tasks."""
from datetime import timedelta

from bodega_core.tasks import GlobalTask
from bodega_legacy_items.item_managers import RktestYmlManager
from bodega_legacy_items.models import JenkinsTask, RktestYml
from django.contrib.contenttypes.models import ContentType
from rkelery import register_task


@register_task
class IdentifyJenkinsTasksTask(GlobalTask):
    @classmethod
    def get_summary(cls, *args, **kwargs):
        return 'Identify outsourced Jenkins tasks.'

    @classmethod
    def get_soft_timeout(cls, *args, **kwargs):
        return timedelta(minutes=30).total_seconds()

    @classmethod
    def get_timeout(cls, *args, **kwargs):
        return timedelta(minutes=35).total_seconds()

    def run(self, *args, **kwargs):
        manager = RktestYmlManager()

        content_type = ContentType.objects.get_for_model(JenkinsTask)
        rktest_ymls_in_recovery = list(
            RktestYml.objects.filter(held_by_content_type=content_type))
        manager.identify_jenkins_tasks(rktest_ymls_in_recovery)
