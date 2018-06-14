# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-05-22 16:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def change_existing_networks(apps, schema_editor):
    IpAddress = apps.get_model('bodega_generic_items', 'IpAddress')
    MssqlServer = apps.get_model('bodega_generic_items', 'MssqlServer')
    UbuntuMachine = apps.get_model('bodega_generic_items', 'UbuntuMachine')
    Network = apps.get_model('bodega_core', 'Network')

    for ubuntu_machine in UbuntuMachine.objects.all():
        location = ubuntu_machine.location
        if location.name == 'AWS-US-WEST-1':
            network = Network.objects.get(location=location,
                                          name='vpc-c77e84a3')
        elif location.name == 'AWS-AP-SOUTH-1':
            network = Network.objects.get(location=location,
                                          name='vpc-966f67ff')
        else:
            network = Network.objects.get(location=location,
                                          name='native')
        ubuntu_machine.network = network
        ubuntu_machine.save()

    for mssql_server in MssqlServer.objects.all():
        location = mssql_server.location
        if location.name == 'AWS-US-WEST-1':
            network = Network.objects.get(location=location,
                                          name='vpc-c77e84a3')
        elif location.name == 'AWS-AP-SOUTH-1':
            network = Network.objects.get(location=location,
                                          name='vpc-966f67ff')
        else:
            network = Network.objects.get(location=location,
                                          name='native')
        mssql_server.network = network
        mssql_server.save()

    for ip_address in IpAddress.objects.all():
        location = ip_address.location
        if location.name == 'AWS-US-WEST-1':
            network = Network.objects.get(location=location,
                                          name='vpc-c77e84a3')
        elif location.name == 'AWS-AP-SOUTH-1':
            network = Network.objects.get(location=location,
                                          name='vpc-966f67ff')
        else:
            network = Network.objects.get(location=location,
                                          name='native')
        ip_address.network = network
        ip_address.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_core', '0013_network'),
        ('bodega_generic_items', '0010_ubuntumachine_add_root_disk_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='ipaddress',
            name='network',
            field=models.ForeignKey(default=1,
                                    help_text='The network of this IpAddress.',
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='bodega_core.Network'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mssqlserver',
            name='network',
            field=models.ForeignKey(default=1,
                                    help_text='The network of this MssqlServer.',
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='bodega_core.Network'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ubuntumachine',
            name='network',
            field=models.ForeignKey(default=1,
                                    help_text='The network of this UbuntuMachine.',
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='bodega_core.Network'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='ubuntumachine',
            name='root_disk_size',
            field=models.IntegerField(choices=[(5, 5), (10, 10), (25, 25)],
                                      default=5,
                                      help_text='Root disk size in GB, one of [5, 10, 25]'),
        ),
        migrations.RunPython(change_existing_networks,
                             reverse_code=migrations.RunPython.noop
        ),
    ]
