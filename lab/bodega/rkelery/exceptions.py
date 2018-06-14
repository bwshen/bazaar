"""RKelery exceptions."""


class TaskException(Exception):
    """A task exception."""

    pass


class TaskStartingTimeoutException(TaskException):
    """An exception while a task was in the STARTED state."""

    pass
