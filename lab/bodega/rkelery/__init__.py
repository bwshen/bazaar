"""RKelery.

This module is essentially a wrapper over Celery modules to standardize on a
simplified subset of usage styles and add our own useful functionality. In
most cases, terminology deliberately mimicks Celery's terminology for ease of
thinking about both. The main additional functionality is:

- Use classes instead of functions for for defining task types.
- Publishing a task returns a task model instance, backed by the Django
  database, containing all information about the published task instead of
  only its result.
- Tasks enter a new RUNNING state from the STARTED state after the task
  implementation has indicated that it's ready to run after synchronzing on
  some condition.
"""
import re
from datetime import datetime, timedelta

import celery
from instrumentation.utils import instrumentation_context
from pytz import utc
from . import states
from .exceptions import TaskStartingTimeoutException
from .utils import arguments_string

default_app_config = 'rkelery.apps.RkeleryAppConfig'

# Global task class registry. This gets populated as a side effect of calling
# register_task, which in turn is usually a side effect of importing a module
# containing task classes. So, to access functionality that depends on this
# registry, the caller needs to have imported all of the task modules even if
# they're neither publishing nor working on those tasks. This seems a little
# hacky, but not sure if there's a better way.
_task_classes = {}


def _get_models():
    """Load the models module.

    We can't import models before the app is ready, so this utility does it at
    runtime when code needs to access the models.
    """
    from . import models
    return models


"""Minimal wrapper for Celery class.

Should probably be extended in the future to avoid leaky abstraction.
"""
Rkelery = celery.Celery


class Task(object):
    """Abstract runtime task instance on the worker.

    An instance of a concrete subclass contains everything to be used by the
    worker while the task is being processed: methods that the concrete
    subclass provides and framework methods those methods can call.

    In this Task class:
    - Static methods provide fixed framework functionality.
    - Class methods provide functionality that can be used outside the worker
      and may be customized by subclasses.
    - Instance methods provide functionality that can only be used by the
      worker processing the task and may be customized by subclasses.
    """

    """The name of the task type if a subclass chooses to customize it.
    When not customized, the task name will be derived from the subclass
    name, which is desirable in most cases.
    """
    name = None

    """The max duration for a task to remain in the STARTED state instead of
    moving on to the RUNNING state. If the task still can't run after this
    time is elapsed, it will give up.

    This defaults to a fairly low value in order to fail fast in case of bugs.
    Most of the time we prefer tasks to be published only when they're likely
    ready to run because the task waiting in the STARTED state still consumes
    time out of its Celery soft/hard time limits. Subclasses can customize this
    value if they have a reason to wait longer. It can be None to indicate an
    infinite time limit, but this is not recommended.
    """
    max_starting_duration = timedelta(seconds=5)

    @staticmethod
    def get_model_instance(task_id):
        """Get the Task model instance for a given task ID."""
        return _get_models().Task.objects.get(task_id=task_id)

    @classmethod
    def get_task_name(cls):
        """Get the task type name.

        Turns a full class name like my_module.tasks.DoSomethingTask and
        creates a task name like "my_module.DoSomething". This should be
        desirable for most cases so subclasses don't need to customize it.
        """
        name = cls.name
        if name is None:
            name = re.sub(r'(.+)Task$', r'\1', cls.__name__)
        module_name = re.sub(r'(.+)\.tasks$', r'\1', cls.__module__)
        return '%s.%s' % (module_name, name)

    @classmethod
    def get_task_display_name(cls):
        """Get a user-friendly display name for the task type.

        Turns a full task type name like "my_module.DoSomething" into just
        "DoSomething". This should be desirable for most cases so subclasses
        don't need to customize it.
        """
        return cls.get_task_name().split('.')[-1]

    @classmethod
    def get_task_summary(cls, task_args, task_kwargs):
        """Get a brief user-friendly summary of a task instance.

        This is used in places outside of the worker processing the task.
        The default implementation calls `get_summary` which is often more
        convenient for subclasses to implement.
        """
        return cls.get_summary(*task_args, **task_kwargs)

    @classmethod
    def get_summary(cls, *args, **kwargs):
        """Get a brief user-friendly summary of a task instance.

        This is used in places outside of the worker processing the task.
        The default implementation creates a generic summary like
        "my_module.DoSomething("arg1", kwarg1="val1"). Subclasses should
        customize it to be something friendlier that incorporates the
        arguments to the task.
        """
        return '%s(%s)' % (cls.get_task_name(), arguments_string(args, kwargs))

    @classmethod
    def get_task_timeout(cls, task_args, task_kwargs):
        """Get the timeout value for a task instance."""
        return cls.get_timeout(*task_args, **task_kwargs)

    @classmethod
    def get_timeout(cls, *args, **kwargs):
        """Get the timeout value for a task instance.

        This is used when a worker runs the task. When we hit this time
        limit, the worker processing the task will be killed and replaced with
        a new worker. If this value is not specified, then it will
        automatically be assigned a default value by Celery according to
        settings.py
        """
        return None

    @classmethod
    def get_task_soft_timeout(cls, task_args, task_kwargs):
        """Get the soft timeout value for a task instance."""
        return cls.get_soft_timeout(*task_args, **task_kwargs)

    @classmethod
    def get_soft_timeout(cls, *args, **kwargs):
        """Get the soft timeout value for a task instance.

        This is used when a worker runs the task. An exception
        celery.exceptions.SoftTimeLimitExceeded is raised when we hit the
        soft time limit that we can choose to catch and handle. If this value
        is not specified, then it will automatically be assigned a default
        value by Celery according to settings.py
        """
        return None

    def __init__(self, celery_task, task_args, task_kwargs):
        """Instantiate a task instance.

        The base implementation saves the internal Celery task instance and
        the arguments to the task. If a subclass overrides this, it needs to
        keep a compatible signature and call this base/super implementation.
        """
        self._celery_task = celery_task
        self.task_args = task_args
        self.task_kwargs = task_kwargs
        self.time_started = datetime.now(utc)

    @property
    def task_id(self):
        """Get the task ID for this task instance.

        An interface for the task implementation on the worker to access its
        task ID.
        """
        return self._celery_task.request.id

    @property
    def model_instance(self):
        """Get the model instance for this task instance.

        A convenience for the task implementation on the worker to access the
        same model instance that's used outside of the worker.
        """
        return Task.get_model_instance(task_id=self.task_id)

    def get_task_blockage_cause(self):
        """Get a loggable cause explaining why this task instance can't run.

        The task will not enter the RUNNING state and call `run_task` / `run`
        until this method returns None. Any other return value indicates that
        the task is blocked and may be logged for diagnosis. This is a way for
        tasks to perform any necessary synchronization. The implementation can
        raise an exception to signal that it wants to give up waiting and fail
        the task.

        The framework will try up to `max_starting_duration` until the task is
        unblocked. If the task type wants to have delays between attempts to
        poll this condition, it can sleep in its implementation.

        The default implementation calls `get_blockage_cause` which is often
        more convenient for subclasses to implement.
        """
        return self.get_blockage_cause(*self.task_args, **self.task_kwargs)

    def get_blockage_cause(self, *args, **kwargs):
        """Get a loggable cause explaining why this task instance can't run.

        A more convenient signature for `get_task_blockage_cause` so
        implementations can automatically bind their chosen names to the
        arguments.

        The default implementation assumes a task requires no synchronization,
        so it immediately returns None.
        """
        return None

    def run_task(self):
        """Run the main functionality of this task instance.

        The framework runs this method when the task enters the RUNNING state.
        Callers must override this or implement `run` which is often more
        convenient.
        """
        return self.run(*self.task_args, **self.task_kwargs)

    def run(self, *args, **kwargs):
        """Run the main functionality of this task instance.

        A more convenient signature for `run_task` so implementations can
        automatically bind their chosen names to the arguments.
        """
        raise NotImplementedError(
            'Task must implement `run` or override `run_task`.')


class Signature(object):
    """A task signature, ready to be published/invoked.

    This is the same concept as Celery signatures, but restricted to the
    simplified style we standardize on and returning task model instances
    when published instead of just results.
    """

    def __init__(self, celery_signature):
        """Instantiate a Signature instance."""
        self._celery_signature = celery_signature

    def _get_result(self, result):
        return _get_models().Task.objects.get(task_id=result.id)

    def apply_async(self, args=(), kwargs={}, **options):
        return self._get_result(self._celery_signature.apply_async(
            args=args, kwargs=kwargs, **options))

    def delay(self, *partial_args, **partial_kwargs):
        return self.apply_async(partial_args, partial_kwargs)


class TaskRegistration(object):
    """A task registration.

    A task registration is the result of applying the register_task decorator
    and, similar the result from Celery's decorators, is the interface for
    callers/clients to create signatures and publish them to get task
    instances.
    """

    def __init__(self, celery_task):
        """Instantiate a TaskRegistration instance."""
        self._celery_task = celery_task

    def apply_async(self, args=[], kwargs={}, **options):
        return self.si(*args, **kwargs).apply_async(**options)

    def delay(self, *args, **kwargs):
        return self.si(*args, **kwargs).delay()

    # For simplicity we choose to use only immutable signatures that leave
    # all task options up to the task publisher, so not including variants
    # like `signature` or `s` here.

    def si(self, *args, **kwargs):
        task_class = get_task_class(self.name)
        celery_signature = self._celery_task.si(*args, **kwargs).set(
            soft_time_limit=task_class.get_task_soft_timeout(args, kwargs),
            time_limit=task_class.get_task_timeout(args, kwargs))

        return Signature(celery_signature)

    @property
    def name(self):
        return self._celery_task.name


def get_task_class(task_name):
    """Get the registered task class for a task name.

    In order for this to work, the caller must have already imported all the
    task modules so that their classes have been registered.
    """
    return _task_classes.get(task_name, Task)


def register_task(cls):
    """Register a task class."""
    if not(isinstance(cls, type) and issubclass(cls, Task)):
        raise TypeError(
            '@register_task needs to be used with a subclass of Task, not %s' %
            repr(cls))

    task_name = cls.get_task_name()
    _task_classes[task_name] = cls

    def run(celery_task, *args, **kwargs):
        task = cls(celery_task, args, kwargs)
        blockage_cause = task.get_task_blockage_cause()
        task_stat_name = task_name.replace('.', '_')
        with instrumentation_context(task_stat_name + '.started'):
            while blockage_cause is not None:
                starting_duration = datetime.now(utc) - task.time_started
                if (task.max_starting_duration is not None and
                   starting_duration > task.max_starting_duration):
                    raise TaskStartingTimeoutException(
                        ('%s timed out for taking %s to start. ' %
                         (task.model_instance, starting_duration)) +
                        ('Task is still blocked because: %s' % blockage_cause))
                blockage_cause = task.get_task_blockage_cause()

        celery_task.update_state(state=states.RUNNING)
        with instrumentation_context(task_stat_name + '.running'):
            task.run_task()

    celery_task = celery.shared_task(name=task_name, bind=True)(run)
    return TaskRegistration(celery_task)


class SynchronizedTask(Task):
    """Abstract task type with generic synchronization functionality.

    The general pattern is that task types indicate which other task instances
    compete for the same resources to be synchronized on. This class provides
    a `get_blockage_reason` implementation which looks for this task instance
    to be the first task waiting for the resources while no other tasks are
    running with those resources.
    """

    def get_blockage_cause(self, *args, **kwargs):
        """Get a loggable cause explaining why this task instance can't run.

        To avoid race conditions, it's very important for the condition that
        we wait on to never become false after it has been true except through
        actions taken by this task instance. So, we indicate that we can run
        once we're at the front of the line with nobody else running.
        """
        if self.task_id is None:
            return None

        models = _get_models()
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
        if (num_running_tasks == 0 and
           self.task_id == first_waiting_task.task_id):
            return None
        return (
            ('%d competitors are running and ' % num_running_tasks) +
            ('the first competitor waiting is %s.' % first_waiting_task))

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
        """Find competitors of this task instance.

        A more convenient signature for `run_task` so implementations can
        automatically bind their chosen names to the arguments.
        """
        raise NotImplementedError(
            'Task must implement `find_competitors` or override ' +
            '`find_competitors_of_task`')


class Group(Signature):
    """A signature group.

    This is the same concept as Celery signatures, but restricted to the
    simplified style we standardize on and returning task model instances
    when published instead of just results.
    """

    def __init__(self, *signatures):
        """Instantiate a Group instance."""
        if len(signatures) == 1:
            self.signatures = signatures[0]
        else:
            self.signatures = signatures
        celery_group = celery.group([
            s._celery_signature for s in self.signatures])
        super(Group, self).__init__(celery_group)

    def _get_result(self, results):
        return [self.signatures[i]._get_result(result)
                for i, result in enumerate(results)]
