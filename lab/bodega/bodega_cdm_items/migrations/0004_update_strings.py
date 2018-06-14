# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-16 16:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_cdm_items', '0003_node_count'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cdmcluster',
            name='artifacts_url',
            field=models.CharField(blank=True, default='', help_text='Tivan style artifacts metadata containing information about the build to install and bootstrap on this CdmCluster.', max_length=255),
        ),
        migrations.AlterField(
            model_name='cdmcluster',
            name='location',
            field=models.ForeignKey(help_text='The location of this CdmCluster.', on_delete=django.db.models.deletion.CASCADE, to='bodega_core.Location'),
        ),
        migrations.AlterField(
            model_name='cdmcluster',
            name='model',
            field=models.CharField(choices=[('aws-m4.xlarge', 'aws-m4.xlarge')], help_text="Model, one of ['aws-m4.xlarge']", max_length=16),
        ),
        migrations.AlterField(
            model_name='cdmcluster',
            name='node_count',
            field=models.IntegerField(default=3, help_text='Number of nodes in this CdmCluster'),
        ),
        migrations.AlterField(
            model_name='cdmnode',
            name='artifacts_url',
            field=models.CharField(blank=True, default='', help_text='Tivan style artifacts metadata containing information about the build to install on this CdmNode.', max_length=255),
        ),
        migrations.AlterField(
            model_name='cdmnode',
            name='location',
            field=models.ForeignKey(help_text='The location of this CdmNode.', on_delete=django.db.models.deletion.CASCADE, to='bodega_core.Location'),
        ),
        migrations.AlterField(
            model_name='cdmnode',
            name='model',
            field=models.CharField(choices=[('aws-m4.xlarge', 'aws-m4.xlarge')], help_text="Model, one of ['aws-m4.xlarge']", max_length=16),
        ),
    ]
