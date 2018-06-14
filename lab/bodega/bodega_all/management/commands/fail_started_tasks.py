"""Cleanup stuck STARTED tasks in Bodega."""

import logging
from celery.task.control import revoke
from django.core.management.base import BaseCommand
from django.db import transaction
from rkelery import states
from rkelery.models import Task

log = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        started_tasks = Task.objects.filter(task_result__status=states.STARTED)
        log.info('%d tasks found in %s state. Setting them all to %s.'
                 % (started_tasks.count(), states.STARTED, states.REVOKED))

        for task in started_tasks:
            with transaction.atomic():
                revoke(task.task_id, terminate=True)
                task_result = task.task_result
                task_result.status = states.REVOKED
                task_result.save()
        log.debug('Done.')
