"""Bodega-specific validation functions."""
import logging
from datetime import timedelta

import yaml

from bodega_core import exceptions
from bodega_core.models import Location, Network, Order
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from sid_from_id.encoder import SidEncoder

log = logging.getLogger(__name__)
MAX_ORDER_TIME_LIMIT = timedelta(hours=48)


def validate_add_items_delta_to_order(data):
    error_msg = ('Adding Items to an existing Order is currently not '
                 'supported.')
    exceptions.bodega_validation_error(log, error_msg)


def validate_order_update_items_delta(data):
    """Validate the items_delta attribute of OrderUpdate.

    We expect the items_delta to be in the following JSON or
    equivalent YML format.

    {
      "nickname_1": {
        "type": "rktest_yml",
        "requirements": {
          "platform": "DYNAPOD"
        }
      },
      "nickname_2": {
        "type": "rktest_yml",
        "requirements": {
          "platform": "DYNAPOD",
          "linux_agent": true
        }
      }
    }
    """
    log.debug('Validating items_delta for OrderUpdate to match '
              'the API. %s' % (repr(data)))
    try:
        items = yaml.safe_load(data)
    except yaml.YAMLError:
        error_msg = '%s is not valid YAML syntax.' % data
        exceptions.bodega_validation_error(log, error_msg)

    if not items:
        log.info('No YAML/JSON data found in provided data.')
        return

    if not isinstance(items, dict):
        error_msg = '"items" dictionary not defined in JSON/YAML data'
        exceptions.bodega_validation_error(log, error_msg)

    for key in items:
        log.debug('Item with nickname %s found in dictionary. Checking '
                  'for all the necessary attributes. %s'
                  % (repr(key), repr(items[key])))
        if 'type' not in items[key]:
            error_msg = 'Type must be defined for each item object.'
            exceptions.bodega_validation_error(log, error_msg)
        elif 'requirements' not in items[key]:
            error_msg = 'Requirements must be defined for each item.'
            exceptions.bodega_validation_error(log, error_msg)
        elif not isinstance(items[key]['requirements'], dict):
            error_msg = 'Requirements must be a dictionary.'
            exceptions.bodega_validation_error(log, error_msg)
        else:
            log.debug('Item (%s) passed all basic validation checks.'
                      % repr(key))


def validate_order_sid_and_owner(order_sid, user):
    try:
        log.debug('Validating sid: %s' % order_sid)

        order = Order.objects.get(sid=order_sid)

        if order.status == Order.STATUS_CLOSED:
            error_msg = ('%s does not have a status '
                         'of %s or %s and therefore cannot be '
                         'updated.' % (str(order),
                                       Order.STATUS_OPEN,
                                       Order.STATUS_FULFILLED))
            exceptions.bodega_validation_error(log, error_msg)

        if order.owner != user and not user.is_superuser:
            error_msg = ('%s does not own %s and is not a '
                         'superuser.' % (repr(user), repr(order)))
            exceptions.bodega_validation_error(log, error_msg)

        return order
    except (ObjectDoesNotExist, ValueError):
        error_msg = '%s is not an existing order SID' % order_sid
        exceptions.bodega_validation_error(log, error_msg)


def validate_order_new_status(new_status, order):
    if not(new_status in
           [choice[0] for choice in Order.STATUS_CHOICES]):
        error_msg = 'Invalid status value: %s' % repr(new_status)
        exceptions.bodega_validation_error(log, error_msg)

    if (order.status == Order.STATUS_FULFILLED and
       new_status == Order.STATUS_CLOSED):
        return

    if (order.status == Order.STATUS_OPEN and
       new_status == Order.STATUS_CLOSED):
        return

    error_msg = ('Invalid order status transition: %s -> %s' %
                 (repr(order.status), repr(new_status)))
    exceptions.bodega_validation_error(log, error_msg)


def validate_order_time_limit(time_limit, user):
    if user.is_superuser:
        # Superusers can assign an indefinitely long time limit
        return

    if time_limit < timedelta():
        error_msg = ('time_limit cannot be negative.')
        exceptions.bodega_validation_error(log, error_msg)

    if time_limit > MAX_ORDER_TIME_LIMIT:
        error_msg = ('Time limit is currently limited to at most %s'
                     % str(MAX_ORDER_TIME_LIMIT))
        exceptions.bodega_validation_error(log, error_msg)


def validate_order_time_limit_delta(time_limit_delta, curr_time, order, user):
    if user.is_superuser:
        # Superusers are allowed to subtract time from Orders as
        # well as assign indefinitely long time limits for Orders
        return

    if time_limit_delta < timedelta():
        error_msg = ('time_limit_delta cannot be negative.')
        exceptions.bodega_validation_error(log, error_msg)

    if order.ejection_time is None:
        time_left = order.time_limit
    else:
        time_left = order.ejection_time - curr_time

    if time_limit_delta + time_left > MAX_ORDER_TIME_LIMIT:
        max_extension = MAX_ORDER_TIME_LIMIT - time_left
        error_msg = ('The time limit is currently limited to at most %s. '
                     'Max possible extension for %s is %s. '
                     % (str(MAX_ORDER_TIME_LIMIT), order, str(max_extension)))
        exceptions.bodega_validation_error(log, error_msg)


def validate_order_ownership_transfer(new_owner_email, new_owner_sid,
                                      order, user):

    if not new_owner_email and not new_owner_sid:
        error_msg = ('Neither a user email or user SID was provided.')
        exceptions.bodega_validation_error(log, error_msg)

    new_owner = None
    if new_owner_email:
        try:
            new_owner = User.objects.get(email=new_owner_email)
        except ObjectDoesNotExist:
            error_msg = ('User with email %s does not exist so cannot '
                         'transfer %s.' % (new_owner_email, order))
            exceptions.bodega_validation_error(log, error_msg)

    if new_owner_sid:
        try:
            encoder = SidEncoder(User)
            new_owner = User.objects.get(id=encoder.decode(new_owner_sid))
        except (ObjectDoesNotExist, ValueError):
            error_msg = ('User with sid %s does not exist so cannot transfer '
                         '%s.' % (new_owner_sid, order))
            exceptions.bodega_validation_error(log, error_msg)

    if user.is_superuser:
        # Superusers can place or transfer Orders on the behalf of other users.
        return new_owner

    if not order:
        error_msg = ('Only superusers can place an Order for other users.')
        exceptions.bodega_validation_error(log, error_msg)

    if order.owner != user:
        error_msg = ('Transferring Order ownership is restricted to superusers'
                     ' and the Order owner.')
        exceptions.bodega_validation_error(log, error_msg)

    return new_owner


def validate_user_is_superuser(user):
    if not user.is_superuser:
        error_msg = 'This action is limited to superusers.'
        exceptions.bodega_validation_error(log, error_msg)


def validate_location_string(location_string):
    try:
        location = Location.objects.get(name=location_string)
        return location
    except ObjectDoesNotExist:
        error_msg = ('%s is not a valid location.' % location_string)
        exceptions.bodega_validation_error(log, error_msg)


def validate_network_string(network_string, location):

    if network_string in getattr(settings, 'UNAVAILABLE_NETWORKS', []):
        error_msg = ('%s is currently unavailable for network.'
                     % network_string)
        exceptions.bodega_validation_error(log, error_msg)

    try:
        network = Network.objects.get(name=network_string, location=location)
        return network
    except ObjectDoesNotExist:
        error_msg = ('%s in location %s is not a valid network.'
                     % (network_string, location.name))
        exceptions.bodega_validation_error(log, error_msg)


def validate_order_update_items_delta_content(data, item_tools, user,
                                              is_maintenance_order):
    items = yaml.safe_load(data)
    for nickname, order_item in items.items():
        item_type = order_item['type']
        item_requirements = order_item['requirements']

        if item_type not in item_tools.item_types:
            error_msg = ('Given type "%s" is not a valid item_type'
                         % item_type)
            exceptions.bodega_validation_error(log, error_msg)

        location = None
        if 'location' in item_requirements:
            location = validate_location_string(item_requirements['location'])

            network_name = item_requirements.get('network', None)
            if network_name:
                validate_network_string(network_name, location)

        encoder = SidEncoder(User)
        user_sid = encoder.encode(user.id)
        item_manager = item_tools.item_types[item_type].manager_class()
        item_manager.validate_item_requirements(item_requirements, user_sid,
                                                is_maintenance_order)
