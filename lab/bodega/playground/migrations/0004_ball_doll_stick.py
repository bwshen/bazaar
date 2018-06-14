# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('playground', '0003_toy_players'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ball',
            fields=[
                ('toy_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='playground.Toy')),
                ('radius', models.FloatField()),
            ],
            options={
            },
            bases=('playground.toy',),
        ),
        migrations.CreateModel(
            name='Doll',
            fields=[
                ('toy_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='playground.Toy')),
                ('sex', models.CharField(max_length=1, choices=[(b'F', b'Female'), (b'M', b'Male')])),
                ('race', models.CharField(max_length=16, choices=[(b'DWARF', b'Dwarf'), (b'ELF', b'Elf'), (b'HUMAN', b'Human'), (b'ORC', b'Orc')])),
            ],
            options={
            },
            bases=('playground.toy',),
        ),
        migrations.CreateModel(
            name='Stick',
            fields=[
                ('toy_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='playground.Toy')),
                ('length', models.FloatField()),
            ],
            options={
            },
            bases=('playground.toy',),
        ),
    ]
