from __future__ import unicode_literals

from django.db import migrations

DEFAULT_LOCATIONS = ['COLO', 'HQ']


def create_default_locations(apps, schema_editor):
    Location = apps.get_model('bodega_core', 'Location')
    for location in DEFAULT_LOCATIONS:
        Location.objects.create(name=location)


def delete_default_locations(apps, schema_editor):
    Location = apps.get_model('bodega_core', 'Location')
    for location in DEFAULT_LOCATIONS:
        Location.objects.get(name=location).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('bodega_core', '0006_location'),
    ]
    operations = [
        migrations.RunPython(create_default_locations,
                             reverse_code=delete_default_locations,
        ),
    ]
