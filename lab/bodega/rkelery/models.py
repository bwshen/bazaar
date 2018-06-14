"""RKelery models."""
import json
from copy import copy
from datetime import datetime
from uuid import uuid4

from bigid_django_celery_results.models import TaskResult
from django.db import models
from pytz import utc
from . import get_task_class, states
from .utils import arguments_string, json_dump


class TaskManager(models.Manager):
    def create(self, **kwargs):
        new_kwargs = copy(kwargs)

        if 'task_id' not in kwargs.keys():
            new_kwargs['task_id'] = str(uuid4())

        if 'task_result' not in kwargs.keys():
            (new_kwargs['task_result'], _) = TaskResult.objects.get_or_create(
                task_id=new_kwargs['task_id'])

        if 'args' in kwargs.keys() and 'args_json' not in kwargs.keys():
            new_kwargs['args_json'] = json_dump(new_kwargs.pop('args'))

        if 'kwargs' in kwargs.keys() and 'kwargs_json' not in kwargs.keys():
            new_kwargs['kwargs_json'] = json_dump(new_kwargs.pop('kwargs'))

        return super(TaskManager, self).create(**new_kwargs)

    def simulate_run_all(self):
        for task in self.filter(task_result__status=states.PENDING):
            task.simulate_run()

    def __filter_tasks(self, **kwargs):
        """Filter tasks efficiently.

        The database doesn't know which filters are the most selective to
        achieve an efficient query plan, but the caller can. Assuming the
        more selective filters (typically on task_result__status) are passed
        in as kwargs, get the matching IDs and then filter on the set of IDs.
        This helps to avoid the severe slowness seen in
        https://rubrik.atlassian.net/browse/INFRA-1718 by restricting the
        caller's less selective filters, applied afterwards, to only the
        tasks matching the selective filters instead of scanning through
        potentially all of task history. Django even translates these into
        nested queries so we don't need to receive the intermediate IDs.
        """
        task_ids = self.filter(**kwargs).values_list('id', flat=True)
        return self.filter(id__in=task_ids)

    def filter_pre_running_tasks(self):
        """Filter pre-RUNNING tasks efficiently."""
        return self.__filter_tasks(
            task_result__status__in=states.PRE_RUNNING_STATES)

    def filter_running_tasks(self):
        """Filter RUNNING tasks efficiently."""
        return self.__filter_tasks(
            task_result__status=states.RUNNING)


class Task(models.Model):
    """Information about a task instance.

    Fields documented at
    http://docs.celeryproject.org/en/latest/internals/protocol.html
    """

    id = models.BigAutoField(primary_key=True)
    task_id = models.CharField(
        max_length=255, null=False, blank=False)

    # Although the Django convention is to avoid null=True with CharField,
    # some of these values can in fact be provided in the Celery protocol
    # message as null. Transforming those null values into empty strings seems
    # to risk confusion in case Celery cares about the distinction, so store
    # the null values as is.

    task = models.CharField(max_length=255, null=False, blank=False)
    root_id = models.CharField(max_length=255, null=True, blank=True)
    parent_id = models.CharField(max_length=255, null=True, blank=True)
    group_id = models.CharField(max_length=255, null=True, blank=True)

    meth = models.CharField(max_length=255, null=True, blank=True)
    shadow = models.CharField(max_length=255, null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)
    retries = models.IntegerField(null=True, blank=True)
    soft_time_limit = models.DurationField(null=True, blank=True)
    hard_time_limit = models.DurationField(null=True, blank=True)
    origin = models.CharField(max_length=255, null=True, blank=True)

    args_json = models.TextField(null=False, blank=False)
    kwargs_json = models.TextField(null=False, blank=False)
    embed_json = models.TextField(null=False, blank=False)

    # Our own fields.
    task_result = models.ForeignKey(
        TaskResult, on_delete=models.CASCADE, null=False, blank=False)
    time_published = models.DateTimeField(null=False, auto_now_add=True)

    objects = TaskManager()

    def __str__(self):
        """Loggable string representation of this task."""
        return '[%s] %s(%s)' % (
            self.task_id, self.task, arguments_string(self.args, self.kwargs))

    # Proeprties to access deserialized JSON fields.

    @property
    def args(self):
        return json.loads(self.args_json)

    @property
    def kwargs(self):
        return json.loads(self.kwargs_json)

    @property
    def embed(self):
        return json.loads(self.embed_json)

    # Properties to access linked tasks.

    @property
    def children(self):
        return Task.objects.filter(parent_id=self.task_id)

    @property
    def parent(self):
        if self.parent_id is None:
            return None
        return Task.objects.get(task_id=self.parent_id)

    @property
    def root(self):
        if self.root_id is None:
            return None
        return Task.objects.get(task_id=self.root_id)

    # Properties to access TaskResult fields.

    @property
    def result(self):
        return self.task_result.result

    @property
    def state(self):
        return self.task_result.status

    @property
    def time_ready(self):
        if self.state in states.READY_STATES:
            return self.time_updated
        else:
            return None

    @property
    def time_updated(self):
        return self.task_result.date_done

    @property
    def wall_time(self):
        if self.time_ready:
            time_end = self.time_ready
        else:
            time_end = datetime.now(utc)
        return time_end - self.time_published

    # Access to functionality from the concrete task class.
    @property
    def task_class(self):
        return get_task_class(self.task)

    def simulate_run(self):
        """Simulate running the task using the current process as the worker.

        This is a way for semi end to end test cases to have the tasks do their
        work. It's pretty hacky as it, for example,  doesn't simulate the
        STARTED state and therefore bypasses synchronization. We should be able
        to get rid of this in favor of unit tests which focus only on verifying
        logic without involving any task framework and real end to end tests
        which include the whole Celery environment. If we really still need a
        simulator after that, we can build a more generic and complete one.
        """
        model_instance = self

        class SimulatedTask(self.task_class):
            @property
            def task_id(self):
                return model_instance.task_id

        try:
            task = SimulatedTask(
                None, model_instance.args, model_instance.kwargs)
            ret = task.run_task()
            self.task_result.result = states.SUCCESS
        except Exception as e:
            ret = e
            self.task_result.result = states.FAILURE

        self.task_result.save()
        return ret
