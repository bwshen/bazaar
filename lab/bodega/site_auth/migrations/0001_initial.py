# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils import timezone

# Note: It's normally a bad practice to directly import models instead of using
# apps.get_model() because the current models are likely out of sync with what
# is in the database. However, the Django built-in User model hasn't had schema
# changes in a very long time, and we need the richer functionality of the full
# model to set hashed passwords.
from django.contrib.auth.models import User
from site_auth.models import create_auth_token


def create_local_admin(apps, schema_editor):
    # Since we're using the full User model, it comes with the pitfall that
    # its signal handlers will be triggered which is not desirable behavior
    # especially for handlers which are meant to be used only after all other
    # migrations have run. Disconnect the signal received by create_auth_token
    # here so we don't prematurely create an auth token for the local admin
    # user.
    #
    # Note: The signal disconnecting takes effect only for the duration of the
    # migration process. It's still connected during the main web application.
    models.signals.post_save.disconnect(
        receiver=create_auth_token, sender=User)

    now = timezone.now()
    local_admin = User(pk=1, username='admin', first_name='Administrator',
                       last_name='Local', is_active=True,
                       is_superuser=True, is_staff=True,
                       last_login=now, date_joined=now)
    local_admin.set_password('admin')
    local_admin.save()
    pass


def remove_local_admin(apps, schema_editor):
    local_admin = User.objects.get(pk=1)
    local_admin.delete()
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_local_admin,
                             reverse_code=remove_local_admin)
    ]
