# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-16 16:46
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_core', '0009_order_tab'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='state',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('DESTROYED', 'Destroyed'), ('MAINTENANCE', 'Maintenance')], default='ACTIVE', help_text="Order status, one of ['ACTIVE', 'DESTROYED', 'MAINTENANCE']", max_length=16),
        ),
        migrations.AlterField(
            model_name='item',
            name='time_held_by_object_updated',
            field=models.DateTimeField(auto_now_add=True, help_text='The last time the holder of this object was updated.'),
        ),
        migrations.AlterField(
            model_name='itemfulfillment',
            name='item',
            field=models.ForeignKey(help_text='The item used to (partially) fulfill the order.', on_delete=django.db.models.deletion.CASCADE, related_name='item_fulfillments', to='bodega_core.Item'),
        ),
        migrations.AlterField(
            model_name='itemfulfillment',
            name='nickname',
            field=models.CharField(help_text='The customer nickname for the required item.', max_length=128),
        ),
        migrations.AlterField(
            model_name='itemfulfillment',
            name='order_update',
            field=models.ForeignKey(help_text='The order update this fulfullment is a part of.', on_delete=django.db.models.deletion.CASCADE, related_name='item_fulfillments', to='bodega_core.OrderUpdate'),
        ),
        migrations.AlterField(
            model_name='order',
            name='maintenance',
            field=models.BooleanField(default=False, help_text='New order is a maintenance order.'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('OPEN', 'Open'), ('FULFILLED', 'Fulfilled'), ('CLOSED', 'Closed')], help_text="Order status, one of ['OPEN', 'FULFILLED', 'CLOSED']", max_length=16),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='comment',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='expiration_time_limit_delta',
            field=models.DurationField(default=datetime.timedelta(0), help_text='Timedelta (Format: [DD] [HH:[MM:]]ss[.uuuuuu]) to extend the current expiration limit.'),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='items_delta',
            field=models.TextField(blank=True, default='', help_text='Items to add to the order.'),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='new_status',
            field=models.CharField(blank=True, choices=[('OPEN', 'Open'), ('FULFILLED', 'Fulfilled'), ('CLOSED', 'Closed')], default='', help_text="Order status, one of ['OPEN', 'FULFILLED', 'CLOSED']", max_length=16),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='order',
            field=models.ForeignKey(help_text='ID of Order object to update', on_delete=django.db.models.deletion.CASCADE, related_name='updates', to='bodega_core.Order'),
        ),
        migrations.AlterField(
            model_name='orderupdate',
            name='time_limit_delta',
            field=models.DurationField(default=datetime.timedelta(0), help_text='Timedelta (Format: [DD] [HH:[MM:]]ss[.uuuuuu]) to extend the current lease'),
        ),
    ]