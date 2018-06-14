# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-01-04 22:06
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_order_owners(apps, schema_editor):
    Order = apps.get_model('bodega_core', 'Order')
    User = apps.get_model('auth', 'User')
    for order in Order.objects.all():
        earliest_update = order.updates.earliest('time_created')
        initial_order_creator = User.objects.get(id=earliest_update.creator_object_id)
        order.owner = initial_order_creator
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bodega_core', '0002_maintenance_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='owned_orders', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='orderupdate',
            name='new_owner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)
        ),
        migrations.RunPython(set_order_owners, reverse_code=migrations.RunPython.noop),
    ]
