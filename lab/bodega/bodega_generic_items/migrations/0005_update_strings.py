# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-16 16:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_generic_items', '0004_disk_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ipaddress',
            name='ip',
            field=models.CharField(help_text='The IPv4 address', max_length=15, unique=True),
        ),
        migrations.AlterField(
            model_name='ipaddress',
            name='location',
            field=models.ForeignKey(help_text='The location of this IpAddress.', on_delete=django.db.models.deletion.CASCADE, to='bodega_core.Location'),
        ),
        migrations.AlterField(
            model_name='mssqlserver',
            name='location',
            field=models.ForeignKey(help_text='The location of this MssqlServer.', on_delete=django.db.models.deletion.CASCADE, to='bodega_core.Location'),
        ),
        migrations.AlterField(
            model_name='mssqlserver',
            name='model',
            field=models.CharField(choices=[('aws-m4.large', 'aws-m4.large'), ('aws-t2.large', 'aws-t2.large')], default='aws-t2.large', help_text="Model, one of ['aws-m4.large', 'aws-t2.large']", max_length=16),
        ),
        migrations.AlterField(
            model_name='mssqlserver',
            name='version',
            field=models.CharField(choices=[('windows2012', 'windows2012')], default='windows2012', help_text="Version, one of ['windows2012']", max_length=16),
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='disk_size',
            field=models.IntegerField(choices=[(32, 32), (64, 64), (128, 128), (256, 256)], default=32, help_text="Disk size in GB, one of ['aws-m4.large', 'aws-m4.xlarge', 'aws-m4.2xlarge', 'aws-t2.large']"),
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='location',
            field=models.ForeignKey(help_text='The location of this UbuntuMachine.', on_delete=django.db.models.deletion.CASCADE, to='bodega_core.Location'),
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='model',
            field=models.CharField(choices=[('aws-m4.large', 'aws-m4.large'), ('aws-m4.xlarge', 'aws-m4.xlarge'), ('aws-m4.2xlarge', 'aws-m4.2xlarge'), ('aws-t2.large', 'aws-t2.large')], default='aws-t2.large', help_text="Model, one of ['aws-m4.large', 'aws-m4.xlarge', 'aws-m4.2xlarge', 'aws-t2.large']", max_length=16),
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='version',
            field=models.CharField(choices=[('14.04', '14.04')], default='14.04', help_text="Version, one of ['14.04']", max_length=16),
        ),
    ]
