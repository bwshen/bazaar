"""Minor variation of django_celery_beat's DatabaseScheduler."""
import django_celery_beat.schedulers


class DatabaseScheduler(django_celery_beat.schedulers.DatabaseScheduler):
    def schedule_changed(self):
        # django_celery_beat.schedulers.DatabaseScheduler seems to do something
        # strange with transactions which leads to an error like
        # "The COMMIT TRANSACTION request has no corresponding BEGIN
        # TRANSACTION" being logged very noisily, at least with our database
        # backend. We don't plan to dynamically update schedules in the
        # database, so just skip this lookup.
        #
        # Swallowing the exception here does not help with the log noise
        # because something lower level is doing the logging. If we ever need
        # to dynamically update schedules, instead reimplement this method
        # without the transaction weirdness which is apparently only a
        # workaround specifically for a MySQL issue.
        return False
