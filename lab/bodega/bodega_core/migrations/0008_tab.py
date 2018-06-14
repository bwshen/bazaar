# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-08-08 16:31

"""Migration for the Tab model."""

from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

DEFAULT_TAB_LIMIT = 1.0


def create_tabs(apps, schema_editor):
    Tab = apps.get_model('bodega_core', 'Tab')
    User = apps.get_model('auth', 'User')
    for user in User.objects.all():
        Tab.objects.create(limit=DEFAULT_TAB_LIMIT, owner=user)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bodega_core', '0007_add_new_locations'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tab',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('limit', models.FloatField()),
                ('owner',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   related_name='tabs',
                                   to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(create_tabs,
                             reverse_code=migrations.RunPython.noop),
    ]