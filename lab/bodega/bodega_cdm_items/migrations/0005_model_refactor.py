# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-04-19 01:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_cdm_items', '0004_update_strings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cdmcluster',
            name='model',
            field=models.CharField(max_length=16),
        ),
        migrations.AlterField(
            model_name='cdmnode',
            name='model',
            field=models.CharField(max_length=16),
        ),
    ]
