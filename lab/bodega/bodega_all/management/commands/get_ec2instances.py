"""Get all EC2 instances creation and destroy times."""
import logging
import os
import sqlite3
from bodega_aws.models import Ec2Instance
from django.core.management.base import BaseCommand
from rkelery.models import Task

log = logging.getLogger(__name__)

DB_FILEPATH = 'ec2_instances.db'
TABLE_NAME = 'ec2_instances'


class EC2InstanceLifeSpan(object):

    def __init__(self, sid, time_created, time_destroyed):
        """Create Ec2instance lifespan object."""
        self.sid = sid
        self.time_created = time_created   # datetime.datetime
        self.time_destroyed = time_destroyed  # datetime.datetime


class Command(BaseCommand):

    def create_dbfile(self, ec2_table):
        """Create a SQLite database."""
        if os.path.exists(DB_FILEPATH):
            os.remove(DB_FILEPATH)
        try:
            conn = sqlite3.connect(DB_FILEPATH)
            c = conn.cursor()
        except Exception as e:
            log.erro('Can\'t connect to database.')
            raise e
        # Create table
        columns = ['sid', 'time_created', 'time_destroyed']
        c.execute('CREATE TABLE {} ({} TEXT PRIMARY KEY, {} '
                  'timestamp, {} timestamp)'.format(TABLE_NAME, columns[0],
                                                    columns[1], columns[2]))
        conn.commit()
        log.info('Creating Table..')
        rows = []
        for obj in ec2_table.values():
            rows.append((obj.sid, obj.time_created, obj.time_destroyed))

        fields = ', '.join(columns)
        sql = 'INSERT INTO {} ({}) VALUES (?,?,?)'.format(TABLE_NAME, fields)
        log.info('Writing data to database..')
        c.executemany(sql, rows)
        conn.commit()
        conn.close()

        log.info('Created ec2_instances.db')

    def handle(self, *args, **options):
        """Get all ec2 instances create and destroy time."""
        ec2_table = {}
        log.info('Retrieving all EC2 Instances..')
        ec2_instances = Ec2Instance.objects.all()
        log.info('Found {} instances'.format(ec2_instances.count()))
        # Update ec2 instance creation time
        count = 1
        for instance in ec2_instances.iterator():
            ec2_table[instance.sid] = \
                EC2InstanceLifeSpan(instance.sid,
                                    instance.held_by.time_created, None)
            count += 1
        log.info('Getting all destroy tasks..')
        destroy_tasks = \
            Task.objects.filter(task='bodega_aws.DestroyEc2Instance')

        for task in destroy_tasks.iterator():
            sid = task.args[0]
            # Take the most recent destroy task time
            if ec2_table[sid].time_destroyed is not None and \
                    (task.time_ready > ec2_table[sid].time_destroyed):
                ec2_table[sid].time_destroyed = task.time_ready
            elif ec2_table[sid].time_destroyed is None:
                ec2_table[sid].time_destroyed = task.time_ready

        # Write to database
        self.create_dbfile(ec2_table)
        log.info('Done')
