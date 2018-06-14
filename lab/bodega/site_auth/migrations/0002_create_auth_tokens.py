# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Note: It's normally a bad practice to directly import models instead of using
# apps.get_model() because the current models are likely out of sync with what
# is in the database. However, the DRF built-in Token model hasn't had schema
# changes in a very long time, and we need the richer functionality of the full
# model to generate tokens. We also need the full User model because it's a
# dependency of the full Token model.
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


def create_auth_tokens(apps, schema_editor):
    for user in User.objects.all():
        Token.objects.create(user=user)


def remove_auth_tokens(apps, schema_editor):
    for token in Token.objects.all():
        token.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('site_auth', '0001_initial'),
        ('authtoken', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_auth_tokens,
                             reverse_code=remove_auth_tokens)
    ]
