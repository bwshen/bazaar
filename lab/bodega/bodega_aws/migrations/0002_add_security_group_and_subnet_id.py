# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-03 06:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_aws', '0001_initial'),
    ]

    # This migration adds a default value for security_group_id and
    # subnet_idi. Since at the time of migration, we only have one Aws Farm
    # in our database, its a safe operation.
    operations = [
        migrations.AddField(
            model_name='awsfarm',
            name='security_group_id',
            field=models.CharField(default='sg-a7cd07c0', max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='awsfarm',
            name='subnet_id',
            field=models.CharField(default='subnet-6aa6330e', max_length=32),
            preserve_default=False,
        ),
    ]
