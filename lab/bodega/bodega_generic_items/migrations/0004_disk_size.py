# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-11-15 18:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_generic_items', '0003_ipaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='ubuntumachine',
            name='disk_size',
            field=models.IntegerField(choices=[(32, 32), (64, 64), (128, 128), (256, 256)], default=32, help_text=b"Disk size in GB, one of ['aws-m4.large', 'aws-m4.xlarge', 'aws-m4.2xlarge', 'aws-t2.large']"),
        ),
        migrations.AlterField(
            model_name='mssqlserver',
            name='model',
            field=models.CharField(choices=[(b'aws-m4.large', b'aws-m4.large'), (b'aws-t2.large', b'aws-t2.large')], default=b'aws-t2.large', help_text=b"Model, one of ['aws-m4.large', 'aws-t2.large']", max_length=16),
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='model',
            field=models.CharField(choices=[(b'aws-m4.large', b'aws-m4.large'), (b'aws-m4.xlarge', b'aws-m4.xlarge'), (b'aws-m4.2xlarge', b'aws-m4.2xlarge'), (b'aws-t2.large', b'aws-t2.large')], default=b'aws-t2.large', help_text=b"Model, one of ['aws-m4.large', 'aws-m4.xlarge', 'aws-m4.2xlarge', 'aws-t2.large']", max_length=16),
        ),
    ]
