# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playground', '0002_toy_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='toy',
            name='players',
            field=models.ManyToManyField(related_name='playing_with_toys', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
