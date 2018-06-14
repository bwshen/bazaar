"""Reference: http://www.django-rest-framework.org/api-guide/serializers/."""

import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from urllib.parse import urlencode

from bodega_core.fields import ItemsField
from bodega_core.models import Order, OrderUpdate, Tab
from bodega_legacy_items.models import JenkinsTask
from django.contrib.auth.models import User
from django.db import transaction
from generic_relations.relations import GenericRelatedField
from pytz import utc
from rest_framework import serializers
from rest_framework.reverse import reverse
from rkelery.models import Task
from sid_from_id.encoder import get_sid
from sid_from_id.serializers import HyperlinkedModelWithSidFromIdSerializer
from . import validators
from .item_types import item_tools, ItemBaseSerializer
from .utils import get_related_url_fields


log = logging.getLogger(__name__)
DEFAULT_ORDER_TIME_LIMIT = timedelta(minutes=240)
DEFAULT_ORDER_EXPIRATION_TIME_LIMIT = timedelta(hours=24)


# Create a user serializer as well, backed by Django's built in user model.
# It's not uncommon to expose the user objects through the REST API so that
# the UI can present directory listings, object ownership, activity logs, etc
# which all relate to the users in the application.
class UserSerializer(HyperlinkedModelWithSidFromIdSerializer):
    live_orders = serializers.SerializerMethodField()

    def get_live_orders(self, user):
        kwargs = {
            'owner_sid': get_sid(user),
            'status_live': True
        }

        orders_url = reverse('order-list', request=self.context['request'])

        return '%s?%s' % (orders_url, urlencode(kwargs))

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Serialized fields for the User class."""

        model = User

        # Note that we choose the fields to expose, in particular NOT exposing
        # the password.
        fields = ('sid', 'url', 'username', 'first_name', 'last_name', 'email',
                  'is_superuser', 'live_orders')

        # For Google logins these fields are just local caches of what's stored
        # in Google. Don't support updating them since that would be confusing.
        read_only_fields = ('username', 'first_name', 'last_name', 'email')


# Create a profile serializer which includes a superset of the fields in the
# user serializer. This is a way to show sensitive fields only to the user
# themselves and not to other users.
class ProfileSerializer(UserSerializer):
    auth_token = serializers.CharField(source='auth_token.key')

    class Meta:
        """Serialized fields for the Profile view."""

        model = User
        fields = UserSerializer.Meta.fields + \
            ('auth_token',)
        read_only_fields = UserSerializer.Meta.read_only_fields + \
            ('auth_token',)


class TabSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the Tab model."""

    charged_live_orders = serializers.SerializerMethodField()

    def get_charged_live_orders(self, tab):
        kwargs = {
            'tab_sid': get_sid(tab),
            'status_live': True
        }

        orders_url = reverse('order-list', request=self.context['request'])

        return '%s?%s' % (orders_url, urlencode(kwargs))

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Serialized fields for the Tab class."""

        model = Tab
        fields = ('sid', 'url', 'limit', 'owner', 'charged_live_orders',)
        read_only_fields = ('owner',)


class TabDetailSerializer(TabSerializer):
    """Detailed Serializer for the Tab model."""

    total_current_charge = serializers.SerializerMethodField()
    total_pending_charge = serializers.SerializerMethodField()

    def get_total_current_charge(self, tab):
        total_current_charge = 0.0
        fulfilled_orders = Order.objects.filter(tab=tab,
                                                status=Order.STATUS_FULFILLED)
        for order in fulfilled_orders:
            items_prices = item_tools.get_prices_for_items(order.items.items())
            order_price = sum(items_prices.values())
            total_current_charge += order_price

        return total_current_charge

    def get_total_pending_charge(self, tab):
        total_pending_charge = 0.0
        open_orders = Order.objects.filter(tab=tab,
                                           status=Order.STATUS_OPEN)
        for order in open_orders:
            items_prices = item_tools.get_prices_for_items(order.items.items())
            order_price = sum(items_prices.values())
            total_pending_charge += order_price

        return total_pending_charge

    class Meta(TabSerializer.Meta):
        fields = TabSerializer.Meta.fields +\
            ('total_current_charge', 'total_pending_charge',)
        read_only_fields = TabSerializer.Meta.read_only_fields +\
            ('total_current_charge', 'total_pending_charge')


class OrderUpdateSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the OrderUpdate model."""

    creator = GenericRelatedField(
        get_related_url_fields(JenkinsTask, User, Task),
        read_only=True)
    new_owner_sid = serializers.CharField(
        required=False,
        write_only=True,
        help_text='SID of user to transfer the Order to.')
    new_owner_email = serializers.CharField(
        required=False,
        write_only=True,
        help_text='Email of user to transfer the Order to.')
    order_sid = serializers.CharField(write_only=True)

    def validate(self, data):
        order = validators.validate_order_sid_and_owner(
            data.pop('order_sid'),
            self.context['request'].user)

        data['creator'] = self.context['request'].user
        data['order'] = order

        if 'items_delta' in data:
            validators.validate_add_items_delta_to_order(data['items_delta'])

        if 'new_status' in data:
            validators.validate_order_new_status(
                data['new_status'], order)

        if 'new_owner_email' in data:
            new_owner = validators.validate_order_ownership_transfer(
                data.pop('new_owner_email'),
                None,
                order,
                self.context['request'].user)
            data['new_owner'] = new_owner

        if 'new_owner_sid' in data:
            new_owner = validators.validate_order_ownership_transfer(
                None,
                data.pop('new_owner_sid'),
                order,
                self.context['request'].user)
            data['new_owner'] = new_owner

        curr_time = datetime.now(utc)
        if 'time_limit_delta' in data:
            validators.validate_order_time_limit_delta(
                data['time_limit_delta'],
                curr_time,
                order,
                self.context['request'].user)

        return super(OrderUpdateSerializer, self).validate(data)

    def create(self, validated_data):
        order = validated_data['order']

        # Materialize the updated status on the order instance.
        if 'new_status' in validated_data:
            order.status = validated_data['new_status']
            if order.status == Order.STATUS_CLOSED:
                order.tab_based_priority = Order.PRIORITY_CLOSED

        # Materialize the updated owner on the order instance.
        if 'new_owner' in validated_data:
            order.owner = validated_data['new_owner']

        with transaction.atomic():
            order.save()
            return super(OrderUpdateSerializer, self).create(validated_data)

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Serialized fields for the OrderUpdate class."""

        model = OrderUpdate

        model_fields = ('sid', 'url', 'creator', 'comment',
                        'expiration_time_limit_delta', 'items_delta',
                        'maintenance', 'new_owner', 'new_status', 'order',
                        'time_limit_delta', 'time_created',)
        non_model_fields = ('new_owner_email', 'new_owner_sid', 'order_sid',)

        fields = model_fields + non_model_fields
        read_only_fields = ('creator', 'maintenance', 'new_owner', 'order',
                            'time_created',)


class OrderSerializer(HyperlinkedModelWithSidFromIdSerializer):
    """Serializer for the Order model."""

    comment = serializers.CharField(write_only=True, required=False)
    ejection_time = serializers.DateTimeField(read_only=True)
    expiration_time = serializers.DateTimeField(read_only=True)
    expiration_time_limit = serializers.DurationField(
        required=False,
        help_text="Expiration time limit of the order in HH:MM:SS format")
    fulfilled_items = serializers.SerializerMethodField()
    items = ItemsField()
    time_limit = serializers.DurationField(
        required=False,
        help_text="Time limit of the order in HH:MM:SS format")
    owner = UserSerializer(read_only=True)
    owner_sid = serializers.CharField(
        required=False,
        help_text="SID of user to place the Order for.",
        write_only=True)
    tab = TabSerializer(read_only=True)
    tab_based_priority = serializers.IntegerField(read_only=True)
    # A read-only field serializing the items field as a JSON object directly
    # in the response. Although this loses non-JSON information the user may
    # have included (particularly comments), it's a much more convenient format
    # to view in the JSON-oriented API browser. Programmatic consumption of the
    # items specification should still use the actual items field.
    items_json = serializers.JSONField(source='items', read_only=True)

    def get_fulfilled_items(self, order):
        # Serialize this order's item fulfillment set looking like [
        #   ItemFulfillment(nickname="a", item=Item(id=1),
        #   ItemFulfillment(nickname="b", item=Item(id=2)
        # ]
        # into a dictionary looking like {
        #   "a": {
        #     <serialized form of Item(id=1)
        #   },
        #   "b": {
        #     <serialized form of Item(id=2)
        #   }
        # }
        fulfilled_items_dict = order.fulfilled_items
        fulfilled_items = OrderedDict()
        for nickname in fulfilled_items_dict:
            fulfilled_items[nickname] = ItemBaseSerializer(
                fulfilled_items_dict[nickname],
                context=self.context
            ).data
        return fulfilled_items

    @transaction.atomic
    def create(self, validated_data):
        comment = validated_data.pop('comment', '')
        items_delta = validated_data.pop('items', None)

        if 'time_limit' in validated_data:
            time_limit = validated_data.pop('time_limit')
        else:
            time_limit = DEFAULT_ORDER_TIME_LIMIT

        if 'expiration_time_limit' in validated_data:
            expiration_time_limit = validated_data.pop('expiration_time_limit')
        else:
            expiration_time_limit = DEFAULT_ORDER_EXPIRATION_TIME_LIMIT

        order = super(OrderSerializer, self).create(validated_data)

        OrderUpdate.objects.create(
            comment=comment,
            creator=self.context['request'].user,
            expiration_time_limit_delta=expiration_time_limit,
            items_delta=items_delta,
            new_owner=validated_data['owner'],
            new_status=validated_data['status'],
            time_limit_delta=time_limit,
            order=order)
        return order

    def validate(self, data):
        data['status'] = Order.STATUS_OPEN

        validators.validate_order_update_items_delta(
            data['items'])

        if data.get('maintenance', False):
            validators.validate_user_is_superuser(self.context['request'].user)

        if 'owner_sid' in data:
            owner = validators.validate_order_ownership_transfer(
                new_owner_email=None,
                new_owner_sid=data.pop('owner_sid'),
                order=None,
                user=self.context['request'].user)
            data['owner'] = owner
        else:
            data['owner'] = self.context['request'].user

        tab = Tab.objects.get(owner=data['owner'])
        data['tab'] = tab

        if 'time_limit' in data:
            validators.validate_order_time_limit(
                data['time_limit'],
                self.context['request'].user)

        validators.validate_order_update_items_delta_content(
            data['items'],
            item_tools,
            self.context['request'].user,
            data.get('maintenance', False))

        return super(OrderSerializer, self).validate(data)

    class Meta(HyperlinkedModelWithSidFromIdSerializer.Meta):
        """Serialized fields for the Order class."""

        model = Order

        fields = ('sid', 'url', 'status', 'items', 'items_json', 'comment',
                  'fulfilled_items', 'ejection_time', 'expiration_time',
                  'expiration_time_limit', 'maintenance', 'time_limit',
                  'owner', 'owner_sid', 'time_created',
                  'time_last_updated', 'tab', 'tab_based_priority', )

        # The user can see what items were assigned to the order but not
        # modify the items in any way.
        read_only_fields = ('fulfilled_items', 'items_json', 'ejection_time',
                            'expiration_time', 'owner', 'status',
                            'time_created', 'time_limit',
                            'time_last_updated', 'tab', 'tab_based_priority',)


class OrderDetailSerializer(OrderSerializer):
    """Detailed serializer for the Order model."""

    item_prices = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    # Only serialize the first ten updates since in most cases, all of the
    # useful information will be materialized there. For orders with many
    # more updates, these will typically just be extensions.
    updates = OrderUpdateSerializer(many=True,
                                    read_only=True,
                                    source='first_few_updates')

    def get_item_prices(self, order):
        item_prices = item_tools.get_prices_for_items(order.items.items())

        return item_prices

    def get_total_price(self, order):
        item_prices = item_tools.get_prices_for_items(order.items.items())
        total_price = sum(item_prices.values())

        return total_price

    def get_fulfilled_items(self, order):
        # Serialize this order's item fulfillment set looking like [
        #   ItemFulfillment(nickname="a", item=Item(id=1),
        #   ItemFulfillment(nickname="b", item=Item(id=2)
        # ]
        # into a dictionary looking like {
        #   "a": {
        #     <serialized form of RktestYml(id=1)
        #   },
        #   "b": {
        #     <serialized form of ReleaseQualBaton(id=2)
        #   }
        # }
        # Use the serializer for each specific Item so the attributes
        # shown in the detailed view
        fulfilled_items_dict = order.fulfilled_items
        fulfilled_items = OrderedDict()
        for nickname in fulfilled_items_dict:
            fulfilled_item = fulfilled_items_dict[nickname]
            serializer_class = item_tools.get_serializer_class(fulfilled_item)
            fulfilled_items[nickname] = serializer_class(
                item_tools.get_specific_item(fulfilled_item),
                context=self.context).data
        return fulfilled_items

    class Meta(OrderSerializer.Meta):
        """Serialized fields for the OrderDetail view."""

        fields = OrderSerializer.Meta.fields +\
            ('item_prices', 'total_price', 'updates',)
        read_only_fields = OrderSerializer.Meta.read_only_fields +\
            ('item_prices', 'total_price', 'updates',)


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(source='task_id', read_only=True)

    type = serializers.CharField(source='task', read_only=True)

    display_type = serializers.SerializerMethodField()

    summary = serializers.SerializerMethodField()

    children = serializers.SerializerMethodField()

    parent = serializers.HyperlinkedRelatedField(
        view_name='task-detail', lookup_field='task_id', lookup_url_kwarg='id',
        read_only=True)

    root = serializers.HyperlinkedRelatedField(
        view_name='task-detail', lookup_field='task_id', lookup_url_kwarg='id',
        read_only=True)

    def get_display_type(self, task):
        return task.task_class.get_task_display_name()

    def get_summary(self, task):
        return task.task_class.get_task_summary(task.args, task.kwargs)

    def get_children(self, task):
        tasks_url = reverse('task-list', request=self.context['request'])
        return '%s?%s' % (tasks_url, urlencode({'parent': task.task_id}))

    class Meta:
        """Serialized fields for the Task class."""

        model = Task
        fields = ('id', 'url', 'type', 'state', 'display_type', 'summary',
                  'soft_time_limit', 'hard_time_limit', 'eta',
                  'time_published', 'time_updated', 'time_ready', 'wall_time',
                  'root', 'parent', 'children', 'group_id', 'origin')
        read_only_fields = ('state', 'summary', 'time_published',
                            'time_updated', 'time_ready', 'wall_time',
                            'group_id', 'origin')
        extra_kwargs = {
            'url': {
                'lookup_field': 'task_id',
                'lookup_url_kwarg': 'id'
            }
        }


class TaskDetailSerializer(TaskSerializer):
    args = serializers.JSONField(read_only=True)

    kwargs = serializers.JSONField(read_only=True)

    class Meta(TaskSerializer.Meta):
        """Serialized fields for the TaskDetail view."""

        fields = TaskSerializer.Meta.fields + ('args', 'kwargs')
        read_only_fields = TaskSerializer.Meta.read_only_fields + (
            'args', 'kwargs')
