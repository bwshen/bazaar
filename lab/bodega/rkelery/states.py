"""RKelery states."""
import celery.states

PENDING = celery.states.PENDING
RECEIVED = celery.states.RECEIVED
STARTED = celery.states.STARTED
SUCCESS = celery.states.SUCCESS
FAILURE = celery.states.FAILURE
REVOKED = celery.states.REVOKED
REJECTED = celery.states.REJECTED
RETRY = celery.states.RETRY
IGNORED = celery.states.IGNORED
REJECTED = celery.states.REJECTED

RUNNING = 'RUNNING'

READY_STATES = celery.states.READY_STATES
UNREADY_STATES = celery.states.UNREADY_STATES.union(frozenset({RUNNING}))
EXCEPTION_STATES = celery.states.EXCEPTION_STATES
PROPAGATE_STATES = celery.states.PROPAGATE_STATES

PRE_RUNNING_STATES = frozenset({PENDING, RECEIVED, STARTED, RETRY})

ALL_STATES = celery.states.ALL_STATES.union(frozenset({RUNNING}))


def choices(states):
    return tuple((state, state) for state in states)
