# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-10 04:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_legacy_items', '0002_rktestyml_tpm'),
    ]

    operations = [
        migrations.AddField(
            model_name='rktestyml',
            name='vcenter_6_5',
            field=models.BooleanField(default=False, help_text='Has VCenter 6.5'),
        ),
    ]
