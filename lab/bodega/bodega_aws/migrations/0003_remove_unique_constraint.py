# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-16 20:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_aws', '0002_add_security_group_and_subnet_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ec2instance',
            name='_name',
            field=models.CharField(max_length=255),
        ),
    ]