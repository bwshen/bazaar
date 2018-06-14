# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-05-02 20:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_generic_items', '0007_model_refactor'),
    ]

    operations = [
        migrations.AddField(
            model_name='ubuntumachine',
            name='root_disk_size',
            field=models.IntegerField(choices=[(5, 5), (10, 10)], default=5, help_text='Root disk size in GB, one of [5, 10]'),
        ),
    ]
