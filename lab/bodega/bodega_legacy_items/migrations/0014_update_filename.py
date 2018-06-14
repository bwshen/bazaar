# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-23 05:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_legacy_items', '0013_update_strings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rktestyml',
            name='filename',
            field=models.CharField(help_text='Filename of the rktest.yml item',
                                   max_length=80, unique=True),
        ),
    ]