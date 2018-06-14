"""Bodega core tasks."""
from django.db.models import Q
from rkelery import _get_models, SynchronizedTask, Task
from rkelery.utils import json_dump


class GlobalTask(SynchronizedTask):
    def find_competitors(self, tasks, *args, **kwargs):
        return tasks.filter(task=self.get_task_name())


class SingleItemTask(SynchronizedTask):
    def find_competitors(self, tasks, item_sid, *args, **kwargs):
        return tasks.filter(
            Q(args_json__contains=json_dump(item_sid)) |
            Q(kwargs_json__contains=json_dump(item_sid)))


class ThrottledTask(Task):
    """Task where only a set number of instances are allowed to run at once."""

    def max_concurrent_tasks(self, *args, **kwargs):
        raise NotImplementedError(
            'Child classes need to implement max_concurrent_tasks.')

    def find_competitors_of_task(self, tasks):
        """Find competitors of this task instance.

        Filter a queryset of tasks to find other tasks which are competing
        for the same synchronized resources as this task instance. This is
        typically done by matching object IDs in the arguments to the tasks.

        The default implementation calls `find_competitors` which is often
        more convenient for subclasses to implement.
        """
        return self.find_competitors(
            tasks, *self.task_args, **self.task_kwargs)

    def find_competitors(self, tasks, *args, **kwargs):
        return tasks.filter(task=self.get_task_name())

    def get_blockage_cause(self, *args, **kwargs):
        if self.task_id is None:
            return None
        models = _get_models()
        max_concurrent_tasks = self.max_concurrent_tasks(args, kwargs)
        # Detect whether we're at the front of the line using the
        # auto-increment ID instead of the publish timestamp. The publish
        # timestamp isn't guaranteed to monotonically increase if there's even
        # slight clock drift between different publishers, so using it could
        # allow a task to jump the line by essentially spoofing an earlier
        # publish timestamp. Although it's sort of cheating to attach this
        # semantic meaning to the primary (surrogate) key, it's also nice to
        # avoid any need for explicit locks and managing all the edge cases
        # they would be subject to.
        waiting_competitors = self.find_competitors_of_task(
            models.Task.objects.filter_pre_running_tasks())
        first_waiting_task = waiting_competitors.earliest('id')
        running_competitors = self.find_competitors_of_task(
            models.Task.objects.filter_running_tasks())
        num_running_tasks = running_competitors.count()
        if (num_running_tasks < max_concurrent_tasks and
           self.task_id == first_waiting_task.task_id):
            return None
        return (
            ('%d competitors are running which exceeds ' % num_running_tasks) +
            ('the maximum allowed of %d. The first competitor waiting is %s.'
             % (max_concurrent_tasks, first_waiting_task)))
