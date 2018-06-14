# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-06-06 23:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bodega_core', '0007_add_new_locations'),
    ]

    operations = [
        migrations.CreateModel(
            name='AwsFarm',
            fields=[
                ('farm_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='bodega_core.Farm')),
                ('region_name', models.CharField(max_length=255)),
                ('aws_access_key_id', models.CharField(max_length=255)),
                ('aws_secret_access_key', models.CharField(max_length=255)),
            ],
            bases=('bodega_core.farm',),
        ),
        migrations.CreateModel(
            name='Ec2Instance',
            fields=[
                ('item_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='bodega_core.Item')),
                ('_name', models.CharField(max_length=255, unique=True)),
                ('instance_id', models.CharField(max_length=255)),
                ('ami_id', models.CharField(max_length=255)),
                ('instance_type', models.CharField(max_length=255)),
                ('farm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bodega_aws.AwsFarm')),
            ],
            options={
                'abstract': False,
            },
            bases=('bodega_core.item',),
        ),
        migrations.AlterUniqueTogether(
            name='awsfarm',
            unique_together=set([('region_name', 'aws_access_key_id', 'aws_secret_access_key')]),
        ),
    ]
