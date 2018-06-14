# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-08-17 02:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_legacy_items', '0008_add_awspod'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rktestyml',
            name='platform',
            field=models.CharField(choices=[('AWSPOD', 'AWSPOD'), ('AZUREPOD', 'AZUREPOD'), ('DYNAPOD', 'DYNAPOD'), ('DYNAPOD_ROBO', 'DYNAPOD_ROBO'), ('PROD_BRIK', 'PROD_BRIK'), ('STATIC', 'STATIC'), ('STATIC_ROBO', 'STATIC_ROBO')], help_text="Platform, one of [u'AWSPOD', u'AZUREPOD', u'DYNAPOD', u'DYNAPOD_ROBO', u'PROD_BRIK', u'STATIC', u'STATIC_ROBO']", max_length=12),
        ),
    ]