"""Fail task in Bodega."""

import logging
from celery.task.control import revoke
from django.core.management.base import BaseCommand
from django.db import transaction
from rkelery import states
from rkelery.models import Task

log = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('task_id', type=str)

    def handle(self, *args, **options):
        task_id = options['task_id']

        try:
            task = Task.objects.get(task_id=task_id)
        except:
            log.error('Could not retrieve task %s.' % task_id)
            raise

        log.info('Setting task %s from state %s to %s.'
                 % (task, task.task_result.status, states.REVOKED))

        with transaction.atomic():
            revoke(task.task_id, terminate=True)
            task_result = task.task_result
            task_result.status = states.REVOKED
            task_result.save()

        log.debug('Done.')
