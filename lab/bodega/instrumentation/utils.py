"""Provides instrumentation context for use within rkelery module."""
import logging
import time
import statsd
from django.conf import settings

log = logging.getLogger(__name__)


def instrumentation_context(context):
    return _InstrumentationContextManager(context)


class _InstrumentationContextManager(object):
    """Context manager class to support instrumentation_context().

    This class is used to instrument code surrounded by instrumentation_context
    For a given context (passed as a param to instrumentation_context), we
    record the time taken and success/exception status
    This is then pushed to statsd. In the future, we can work to make this
    class support more stats backends
    """

    _stats_client = None

    @classmethod
    def _get_stats_client(cls):
        """Return the statsd client, after initialising it if necessary."""
        # First call to this method initialises the stats_client (as opposed
        # to initialising it at the time of class load). This is because
        # the stats_client requires the STATSD_HOST and STATSD_PORT
        # configurations to be available. These are avaialble only after
        # the django app is initialised and ready.
        if cls._stats_client is None:
            cls._stats_client = statsd.StatsClient(
                settings.STATSD_HOST,
                settings.STATSD_PORT,
                prefix='internal.monitoring.bodega.tasks')
        return cls._stats_client

    def __init__(self, context):
        self.context = context
        self.start_time = None  # Initialised in the __enter__ method

    def __enter__(self):
        self.start_time = time.time()
        return None

    def __exit__(self, exception_type, exception_value, exception_trace):
        try:
            stop_time = time.time()
            if exception_type is not None:
                stat_name = "%s.exceptions.%s" % (
                    self.context, exception_type.__name__)
                _InstrumentationContextManager._get_stats_client().incr(
                    stat_name)
            duration = int(stop_time - self.start_time)
            _InstrumentationContextManager._get_stats_client().timing(
                self.context, duration)
            _InstrumentationContextManager._get_stats_client().incr(
                self.context)
        except:
            log.error("Could not publish metrics", exc_info=1)
        finally:
            # Returning False here guarantees that the context manager never
            # suppresses any exception that was raised from within the
            # block of user code it surrounds.
            return False
