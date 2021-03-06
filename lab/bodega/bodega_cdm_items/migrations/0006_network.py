# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-05-22 16:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def change_existing_networks(apps, schema_editor):
    CdmNode = apps.get_model('bodega_cdm_items', 'CdmNode')
    CdmCluster = apps.get_model('bodega_cdm_items', 'CdmCluster')
    Network = apps.get_model('bodega_core', 'Network')

    for cdm_node in CdmNode.objects.all():
        location = cdm_node.location
        if location.name == 'AWS-US-WEST-1':
            network = Network.objects.get(location=location,
                                          name='vpc-c77e84a3')
        elif location.name == 'AWS-AP-SOUTH-1':
            network = Network.objects.get(location=location,
                                          name='vpc-966f67ff')
        else:
            network = Network.objects.get(location=location,
                                          name='native')
        cdm_node.network = network
        cdm_node.save()

    for cdm_cluster in CdmCluster.objects.all():
        location = cdm_cluster.location
        if location.name == 'AWS-US-WEST-1':
            network = Network.objects.get(location=location,
                                          name='vpc-c77e84a3')
        elif location.name == 'AWS-AP-SOUTH-1':
            network = Network.objects.get(location=location,
                                          name='vpc-966f67ff')
        else:
            network = Network.objects.get(location=location,
                                          name='native')
        cdm_cluster.network = network
        cdm_cluster.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_core', '0013_network'),
        ('bodega_cdm_items', '0005_model_refactor'),
    ]

    operations = [
        migrations.AddField(
            model_name='cdmcluster',
            name='network',
            field=models.ForeignKey(default=1,
                                    help_text='The network of this CdmCluster.',
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='bodega_core.Network'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cdmnode',
            name='network',
            field=models.ForeignKey(default=1,
                                    help_text='The network of this CdmNode.',
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='bodega_core.Network'),
            preserve_default=False,
        ),
        migrations.RunPython(change_existing_networks,
                             reverse_code=migrations.RunPython.noop
        ),
    ]
