# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-03-29 15:39
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


def set_order_expiration_time_limits(apps, schema_editor):
    Order = apps.get_model('bodega_core', 'Order')
    for order in Order.objects.all():
        earliest_update = order.updates.earliest('time_created')
        earliest_update.expiration_time_limit_delta = \
            datetime.timedelta(hours=24)
        earliest_update.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_core', '0004_farm_seed'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderupdate',
            name='expiration_time_limit_delta',
            field=models.DurationField(
                default=datetime.timedelta(0),
                help_text=(b'Timedelta (Format: [DD] [HH:[MM:]]ss[.uuuuuu]) '
                           b'to extend the current expiration limit.')),
        ),
        migrations.RunPython(set_order_expiration_time_limits,
                             reverse_code=migrations.RunPython.noop)
    ]