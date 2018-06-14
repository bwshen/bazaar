"""Analyze AWS costs.

The idea is to get all active orders and ec2 instances
within a given time range.

The basic workflow is as follows:
1. Find Active Orders within time range
2. Analyze costs from orders
3. Find Active Ec2Instances within time range
4. Analyze costs from ec2instances
-------------
Note: This script doesn't implement a way to calculate overhead for
orders. Preparing order items takes additional time which hasn't
been accounted for in this script yet.

######################################################################
Please run `./manage.py get_ec2instances` prior to using this command.
######################################################################
"""
import collections
import logging
import math
import sqlite3
from datetime import datetime, timedelta
import dateutil.parser
import pytz
from bodega_aws.models import Ec2Instance
from bodega_cdm_items.models import CdmCluster, CdmNode
from bodega_core.models import Item, Order
from bodega_generic_items.models import MssqlServer, UbuntuMachine
from bodega_sd_dev_items.models import SdDevMachine
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

log = logging.getLogger(__name__)

DB_FILEPATH = 'ec2_instances.db'
TABLE_NAME = 'ec2_instances'
TABLE_COLUMNS = ['sid', 'time_created', 'time_destroyed']
AWS_LOCATIONS = ('AWS-US-WEST-1', 'AWS-AP-SOUTH-1')
EC2_COST_TABLE = {
    'AWS-US-WEST-1': {
        'aws-m4.2xlarge': 0.4680,
        'aws-m4.xlarge': 0.2340,
        'aws-m4.large': 0.1170,
        'aws-t2.large': 0.1104,
        'aws-t2.medium': 0.0552,
        'aws-t2.small': 0.0276,
        'aws-t2.micro': 0.01380,
    },
    'AWS-AP-SOUTH-1': {
        'aws-m4.2xlarge': 0.4200,
        'aws-m4.xlarge': 0.2100,
        'aws-m4.large': 0.1050,
        'aws-t2.large': 0.0992,
        'aws-t2.medium': 0.0496,
        'aws-t2.small': 0.0248,
        'aws-t2.micro': 0.0124,
    }
}


class Command(BaseCommand):
    help = 'Analyse AWS usage to identify leakages'

    def __init__(self, *args, **kwargs):
        """Define start_date and end_date."""
        super().__init__(*args, **kwargs)
        self.start_date = None  # datetime.datetime
        self.end_date = None  # datetime.datetime

    def add_arguments(self, parser):
        parser.add_argument('start_date', nargs='?', type=str)
        parser.add_argument('end_date', nargs='?', type=str)

    def get_aws_orders(self):
        # Get all orders created before the end_date
        log.info('Filtering orders created before end_date')
        orders = Order.objects.filter(
            time_created__lte=self.end_date).exclude(status=Order.STATUS_OPEN)
        log.info('Found {} orders'.format(orders.count()))
        aws_orders = []
        log.info('Filtering AWS Orders')
        skip_count = 0
        for order in orders.iterator():
            if self.skip_this_order(order):
                # log.info('Skipping order: {}'.format(order.sid))
                skip_count += 1
                continue
            aws_orders.append(order)

        log.info('Found {} AWS orders, skipped {}'.format(len(aws_orders),
                                                          skip_count))
        return aws_orders

    def skip_this_order(self, order):
        return \
            self.skip_if_not_correct_location(order) or \
            self.skip_if_order_fulfillment_time_invalid(order) or \
            self.skip_if_order_closed_before_start_date(order)

    def skip_if_not_correct_location(self, order):
        """
        Skip if order not in AWS location.

        Sample item json:
        {
            "_jenkins_node": {
                "requirements": {
                    "privileged_mode": true,
                    "version": "3de6e760c4e4e85215d2a0dfa9614f76db224f00",
                    "location": "COLO"
                },
                "type": "sd_dev_machine"
            },
            "pod": {
                "requirements": {
                    "platform": "DYNAPOD",
                    "location": "COLO"
                },
                "type": "rktest_yml"
            }
        }
        """
        skip = True
        try:
            for item_name in order.items.keys():
                item_dict = order.items[item_name]
                if 'requirements' in item_dict and \
                        isinstance(item_dict['requirements'], dict) and \
                        'location' in item_dict['requirements']:
                    location = item_dict['requirements']['location']
                    if location and isinstance(location, str) and \
                            location.upper() in AWS_LOCATIONS:
                        skip = False
                        break
        except:
            pass
        return skip

    def skip_if_order_fulfillment_time_invalid(self, order):
        """
        Skip order if the fulfillment time is not valid.

        Case 1: No order fulfillment time (order never fulfilled)
        Case 2: fulfillment time > end date
        """
        if not order.fulfillment_time:
            return True
        if order.fulfillment_time > self.end_date:
            return True

        return False

    def skip_if_order_closed_before_start_date(self, order):
        """Skip order if closed prior to start_date."""
        if not order.STATUS_CLOSED:
            return False
        updates = order.updates.filter(new_status=Order.STATUS_CLOSED)
        if updates.count() > 0 and updates[0].time_created < self.start_date:
            return True
        return False

    def get_aws_model_for_item(self, item_details):
        item_type = item_details['type'].lower()
        requirements = item_details['requirements']
        model = requirements.get('model', None)
        if model:
            return model.lower()
        if item_type == 'sd_dev_machine':
            return SdDevMachine.MODEL_AWS_M4_LARGE
        elif item_type == 'ubuntu_machine':
            return UbuntuMachine.DEFAULT_MODEL
        elif item_type == 'mssql_server':
            return MssqlServer.DEFAULT_MODEL
        return CdmNode.DEFAULT_MODEL

    def get_order_timespan_in_hours(self, order):
        order_status = order.status.upper()
        order_start_time = None
        order_end_time = None

        order_start_time = max(order.fulfillment_time, self.start_date)

        if order.status == order.STATUS_CLOSED:
            order_close_time = order.updates.filter(
                new_status=Order.STATUS_CLOSED)[0].time_created
            order_end_time = min(order_close_time, self.end_date)
        elif order_status == order.STATUS_FULFILLED:
            order_end_time = self.end_date

        return (order_end_time - order_start_time).total_seconds() / 3600

    def calculate_cost_from_orders(self, aws_orders):
        """
        Calculate cost for orders.

        Sample item json:
        {
           "item_1": {
                "requirements": {
                    "version": "3de6e760c4e4e85215d2a0dfa9614f76db224f00",
                    "location": "COLO"
                },
                "type": "sd_dev_machine"
            },
            "item_2": {
                "requirements": {
                    "privileged_mode": true,
                    "version": "3de6e760c4e4e85215d2a0dfa9614f76db224f00",
                    "location": "AWS-US-WEST-1",
                    "model": "m4.xlarge"
                },
                "type": "sd_dev_machine"
            },
            "item_3": {
                "requirements": {
                    "location": "AWS-US-WEST-1"
                },
                "type": "mssql_server"
            }
        }
        """
        timespan_dict = \
            {location: collections.defaultdict(lambda: collections.defaultdict(
                lambda: {'hours': 0.0, 'nodes': 0})) for
             location in AWS_LOCATIONS}
        log.info('Total orders to analyze: {}'.format(len(aws_orders)))

        for order in aws_orders:
            for item_name in order.items.keys():
                item_details = order.items[item_name]
                item_type = item_details['type'].lower()
                item_location = \
                    item_details['requirements']['location'].upper()
                if item_location not in AWS_LOCATIONS:
                    continue
                item_model = self.get_aws_model_for_item(item_details)
                node_count = 1
                if item_type == 'cdm_cluster':
                    node_count = order.items[item_name]['requirements'].get(
                        'node_count', CdmCluster.DEFAULT_NODE_COUNT)
                order_time_span = \
                    node_count * self.get_order_timespan_in_hours(order)
                timespan_dict[item_location][item_model][item_type]['hours']\
                    += order_time_span
                timespan_dict[item_location][item_model][item_type]['nodes']\
                    += node_count
        # Calculate costs
        log.info('Order Costs:')
        the_dollars = round(self.get_total_cost_for_orders(timespan_dict), 2)
        return the_dollars

    def get_total_cost(self, timespan_by_location):
        total_cost = 0.0
        for aws_location in timespan_by_location:
            timespan_by_models = timespan_by_location[aws_location]
            for model, stats in timespan_by_models.items():
                model_cost = math.ceil(stats['hours']) * self.\
                    get_ec2_instance_cost_per_hour(model, aws_location)
                log.info('({} {}) - Time: {} hrs, Nodes: {}, Cost: ${}'.format(
                    model, aws_location, round(stats['hours'], 2),
                    stats['nodes'], round(model_cost, 2)))
                total_cost += model_cost
        return total_cost

    def get_total_cost_for_orders(self, timespan_by_location):
        total_cost = 0.0
        model_cost = 0.0
        item_cost = 0.0
        for aws_location in timespan_by_location:
            timespan_by_models = timespan_by_location[aws_location]
            for model in timespan_by_models:
                timespan_by_items = timespan_by_models[model]
                for item_type, stats in timespan_by_items.items():
                    item_cost = \
                        math.ceil(stats['hours']) * \
                        self.get_ec2_instance_cost_per_hour(model,
                                                            aws_location)
                    log.info('({} {} {}) - Time: {} hrs, Nodes: {}, Cost: '
                             '${}'.format(aws_location, model, item_type,
                                          round(stats['hours'], 2),
                                          stats['nodes'],
                                          round(item_cost, 2)))

                model_cost += item_cost
            total_cost += model_cost
        return total_cost

    def get_ec2_instance_cost_per_hour(self, model='aws-m4.xlarge',
                                       location='AWS-US-WEST-1'):
        """Link: https://www.ec2instances.info/?region=us-west-1."""
        try:
            return EC2_COST_TABLE[location][model]
        except KeyError:
            log.warn("Data not available for AWS model "
                     "{} in {} location".format(model, location))
            return 0.4680

    def get_ec2_instances_list(self):
        """Get list of ec2_instances created before given date."""
        try:
            db = sqlite3.connect(DB_FILEPATH)
            cursor = db.cursor()
        except Exception as e:
            raise e
        table_name = cursor.execute("SELECT name FROM sqlite_master "
                                    "WHERE type='table'").fetchone()[0]
        cursor.execute("SELECT * from {} where time_created"
                       "<=?".format(table_name), (self.end_date, ))
        ec2_instances = cursor.fetchall()
        db.close()

        return ec2_instances

    def calculate_costs_from_ec2instances(self):
        """
        Calculate costs from ec2_instance instances information.

        Run `./manage.py get_ec2instances` prior.
        """
        log.info('Retrieving EC2 instances')
        ec2_instances_rows = self.get_ec2_instances_list()
        log.info('Found {} EC2 instances'.format(len(ec2_instances_rows)))
        timespan_by_location = {location: collections.defaultdict(
            lambda: {'hours': 0.0, 'nodes': 0}) for location in AWS_LOCATIONS}

        the_dollars = 0.0
        items_skipped = 0
        # row = [sid, time_created, time_destroyed]
        for row in ec2_instances_rows:

            sid = row[0]  # sid
            create_time = dateutil.parser.parse(row[1])
            destroy_time = dateutil.parser.parse(row[2]) if row[2] else None
            instance_object = Ec2Instance.objects.filter(sid=sid)[0]
            # Ignore destroyed items with no destroy times
            # Ignore item if destroy time is before input time range
            if destroy_time is None and \
                    instance_object.state == Item.STATE_DESTROYED:
                items_skipped += 1
                continue
            elif destroy_time is not None and destroy_time < self.start_date:
                continue
            # Adjust (destroy) time for active and maintenance items
            if destroy_time is None:
                destroy_time = timezone.now()
            # Querying object to get model and location
            model = 'aws-' + instance_object.instance_type
            location = instance_object.held_by.location.name
            # Adjust create/destroy times as per input times
            create_time = max(self.start_date, create_time)
            destroy_time = min(self.end_date, destroy_time)

            uptime = (destroy_time - create_time).total_seconds() / 3600
            timespan_by_location[location][model]['hours'] += uptime
            timespan_by_location[location][model]['nodes'] += 1

        log.info('{} items were skipped because item didn\'t '
                 'have a destroy time but had a DESTROYED '
                 'state'.format(items_skipped))
        log.info('EC2 instance costs:')
        the_dollars = round(self.get_total_cost(timespan_by_location), 2)

        return the_dollars

    def main(self):
        aws_orders = self.get_aws_orders()
        bodega_order_dollars = self.calculate_cost_from_orders(aws_orders)
        bodega_ec2_dollars = \
            self.calculate_costs_from_ec2instances()

        log.info('Cost calculated by analysing Orders: ${}'.format(
            bodega_order_dollars))
        log.info('Cost calculated by analysing Ec2Instances: '
                 '${}'.format(bodega_ec2_dollars))

        questionable_dollars = abs(bodega_ec2_dollars - bodega_order_dollars)
        if questionable_dollars:
            log.info('There is a difference of ${}'.format(
                round(questionable_dollars, 2)))

    def handle(self, *args, **options):
        # default values
        self.end_date = timezone.now()
        self.start_date = self.end_date - timedelta(days=30)
        # Try to parse used provided values
        for name in ('start_date', 'end_date'):
            if name not in options:
                log.info('{} not provided by user, using {} as the value '
                         'for it'.format(name, getattr(self, name)))
                continue
            try:
                value = pytz.utc.localize(datetime.strptime(options[name],
                                                            "%m-%d-%Y"))
                setattr(self, name, value)
            except ValueError:
                raise CommandError('Incorrect date format. '
                                   'Please use mm-dd-yy.')
        if self.start_date > self.end_date:
            log.error('End date is earlier than Start date.')
            return
        self.main()
