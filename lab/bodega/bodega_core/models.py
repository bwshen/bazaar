"""The Django models of the application."""

import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from operator import attrgetter

import rkelery.states
import yaml
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from memoize import memoize
from pytz import utc
from rkelery.models import Task

from sid_from_id.models import ModelWithSidFromId

log = logging.getLogger(__name__)

#
# Models representing the state of a Bodega instance.
#
# We use a bar/restaurant analogy where customers (clients/users) place
# orders (requests) for items (test resources) they intend to consume in one
# sitting (Jenkins job or private run). The orders enter a queue until they
# can be fulfilled by Bodega doing whatever is necessary behind the scenes to
# make the ordered items available. When customers are done consuming their
# items, they close their order so Bodega can clean up what's left of the
# items.


class BaseModel(ModelWithSidFromId, models.Model):
    """An abstract base model class for all Bodega models.

    Just used to add some common conveniences.
    """

    id = models.BigAutoField(primary_key=True)

    class Meta:
        """Meta class."""

        abstract = True

    def __str__(self):
        """Build a general string representation.

        The format indicates the model sid and the essential name-value pairs
        for identifying the model instance.
        """
        info_nvps = [
            ('sid', self.sid)
        ] + self.__str_additional_info_nvps__()
        # Create a "name=val" string for each name-value pair, then concatenate
        # them all together, separated by commas.
        info_str = ', '.join([
            '%s=%s' % (name, str(val)) for (name, val) in info_nvps])
        return '%s(%s)' % (self.__class__.__name__, info_str)

    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return []


class Farm(BaseModel):
    """Generic class representing different sources of Items."""

    def can_grow(self, item):
        """Farm can produce this specified item."""
        raise NotImplementedError('Child class must implement can_grow')


class Item(BaseModel):
    """A generic item that can fulfill a part of an order."""

    # ACTIVE means the Item exists and can be used to fulfill an Order
    STATE_ACTIVE = 'ACTIVE'

    # DESTROYED means the Item was removed from the underlying datastores and
    # can no longer be used. The Item is still kept in the database for record
    # keeping purposes.
    STATE_DESTROYED = 'DESTROYED'

    # MAINTENANCE means the Item needs to be held by a special Order request.
    # An Item that is marked for maintenance is freed after an Order or
    # JenkinsTask is finished with the Item. This Item will then only be used
    # to fulfill maintenance Orders.
    STATE_MAINTENANCE = 'MAINTENANCE'

    STATE_CHOICES = (
        (STATE_ACTIVE, 'Active'),
        (STATE_DESTROYED, 'Destroyed'),
        (STATE_MAINTENANCE, 'Maintenance'),
    )

    state = models.CharField(
        max_length=16,
        default=STATE_ACTIVE,
        choices=STATE_CHOICES,
        help_text='Order status, one of %s' %
                  repr([choice[0] for choice in STATE_CHOICES]))

    # Raw fields for tracking which object currently holds the item.
    # Do NOT access these directly; use the held_by property below instead.
    held_by_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True)
    held_by_object_id = models.PositiveIntegerField(null=True, blank=True)
    held_by_object = GenericForeignKey(
        'held_by_content_type', 'held_by_object_id')
    time_held_by_object_updated = models.DateTimeField(
        auto_now_add=True,
        help_text='The last time the holder of this object was updated.')

    # An item should have a name, but rather than store a field for all items
    # each subtype should provide its own property implementation.
    @property
    def name(self):
        return str(self)

    # An item may potentially be held by any generic model instance. The main
    # possibilities are:
    # - an order which this item is helping to fulfill
    # - a maintenance task (to be added in the future) that's working on
    #   preparing or cleaning up this item
    # - an admin user who's working on manually troubleshooting or recovering
    #   this item
    # - (potential future feature) another "combo" item which contains this
    #   item
    # In any case, the purpose of tracking who/what is holding the item is to
    # cooperatively ensure that the holder has exclusive control of the item
    # and won't be getting interference from something else. This is similar to
    # the purpose of a lock, but (for now) we don't intend to support semantics
    # such as queueing/waiting for the lock. Instead, we prefer for potential
    # holders to be looking for other items, and this field is only for
    # avoiding ambiguity about who/what holds the item. If something thinks
    # they are holding it but this field indicates otherwise, they should
    # abort.
    @property
    def held_by(self):
        return self.held_by_object

    @held_by.setter
    def held_by(self, held_by):
        self.held_by_object = held_by
        self.time_held_by_object_updated = datetime.now(utc)

    @property
    def time_held_by_updated(self):
        return self.time_held_by_object_updated

    @property
    def held_by_object_in_final_state(self):
        """Whether the item is definitely held by an object in its final state.

        Perform this check in a way that's resilient to race conditions from
        concurrent access. See https://rubrik.atlassian.net/browse/INFRA-860
        for the kind of problem that a race condition can cause.

        The ideal implementation may theoretically be to use
        https://docs.djangoproject.com/en/1.10/ref/models/querysets/#select-for-update
        but it seems not too well supported as most database backends
        (including MS SQL, as we currently use) do not support it. Instead,
        our implementation relies on the semantics of final states to do
        additional comparisons without locks.
        """
        # Take note of what is initially holding the item so we can check
        # against it later.
        initially_held_by = self.held_by

        # Test whether a holder object is one in a final state. This is a
        # private implementation out of paranoia to carefully whitelist the
        # exact set of final object states for the purpose of this method.
        def is_in_final_state(holder):
            if isinstance(holder, Order):
                order = holder
                return order.status == Order.STATUS_CLOSED
            elif isinstance(holder, Task):
                task = holder
                return task.state in rkelery.states.READY_STATES
            else:
                return False

        # If the initial holder is not currently in a final state, then things
        # may still be in flux.
        if not is_in_final_state(initially_held_by):
            return False

        # Find out what is currently holding the item.
        self.refresh_from_db()
        now_held_by = self.held_by

        # If the current holder is different from the initial holder, then
        # things still seem to be in flux.
        if now_held_by != initially_held_by:
            # This is the race condition we're trying to catch. Log a debug
            # message here so that we know when it happens, but not elsewhere
            # since it would be fairly spammy when it didn't happen.
            log.debug(
                ('%s was initially held by ' % repr(self)) +
                ('%s which is a final state, but ' % repr(initially_held_by)) +
                ('now the item is held by %s. ' % repr(now_held_by)) +
                ('This is due to concurrent access so the current holder ') +
                ('may still be actively working with the item.'))
            return False

        # At this point, we've passed all the checks above so:
        #   1. The item was initially held by some object H.
        #   2. H is currently in a final state.
        #   3. The item is currently held by H.
        # We can confidently conclude that the item is currently held by H,
        # an object of a final state. This fact will not be changing because H
        # is in a final state.
        return True


class ItemFulfillment(BaseModel):
    """A record of an individual item fulfilling part of an order."""

    order_update = models.ForeignKey(
        'OrderUpdate', on_delete=models.CASCADE,
        related_name='item_fulfillments',
        help_text='The order update this fulfillment is a part of.')

    nickname = models.CharField(
        max_length=128,
        help_text='The customer nickname for the required item.')

    item = models.ForeignKey(
        'Item', on_delete=models.CASCADE,
        related_name='item_fulfillments',
        help_text='The item used to (partially) fulfill the order.')

    def __str_additional_info_nvps__(self):
        """Get additional name-value pairs for the string representation."""
        return [
            ('order_update', str(self.order_update)),
            ('nickname', repr(self.nickname)),
            ('item', str(self.item))
        ]


class Location(BaseModel):
    """Class representing the different locations that Bodega supports."""

    name = models.CharField(max_length=16,
                            blank=False,
                            null=False,
                            unique=True)


class Network(BaseModel):
    """Class representing the different networks that Bodega supports."""

    location = models.ForeignKey(Location, null=False)
    name = models.CharField(max_length=16,
                            blank=False,
                            null=False)

    class Meta:
        """Metadata for Network."""

        unique_together = ('location',
                           'name')


class Order(BaseModel):
    """An order for items to be consumed in a sitting.

    There is currently no separate model for a sitting/session. The order,
    especially its status, implicitly tracks the sitting.
    """

    # When an order is FULFILLED or CLOSED, we set the last known priority
    # of the order to a special value.
    PRIORITY_FULFILLED = PRIORITY_CLOSED = -1

    # OPEN means the order has been placed and is waiting to be fulfilled. An
    # order immediately starts with an OPEN status after a customer places it.
    # In the future, we may consider adding some kind of "new" or "pending"
    # status to represent orders that have been placed but, for whatever
    # reason, not yet acknowledged by Bodega and may potentially require
    # customer action or be rejected.
    STATUS_OPEN = 'OPEN'

    # FULFILLED means all the items in the order are available and ready for
    # the customer to consume. An order status continues to be FULFILLED until
    # the customer closes it. In the future, since we'll need to auto-close
    # fulfilled orders that have been idle for a long time, we'll also need
    # some mechanism for customers to indicate that they're still consuming
    # their items for preventing the auto-close. We may represent that with
    # additional status values.
    STATUS_FULFILLED = 'FULFILLED'

    # CLOSED means the customer has finished consuming all the items in the
    # order, so they are ready for cleanup. In the future, we may add
    # additional status values to represent other ways that an order can be
    # finalized, like cancelled or auto-closed.
    STATUS_CLOSED = 'CLOSED'

    STATUS_CHOICES = (
        (STATUS_OPEN, 'Open'),
        (STATUS_FULFILLED, 'Fulfilled'),
        (STATUS_CLOSED, 'Closed')
    )

    # The status of the order.
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        help_text='Order status, one of %s' %
                  repr([choice[0] for choice in STATUS_CHOICES]))

    holding_items = GenericRelation(
        'Item',
        content_type_field='held_by_content_type',
        object_id_field='held_by_object_id')

    # Default value for priority will be -1, this field is updated
    # by the fulfiller when it calculates the priority of each order.
    # This field is mainly used to sort the order endpoint based on
    # last known priority of the order.
    tab_based_priority = models.IntegerField(
        default=PRIORITY_CLOSED,
        help_text='Last known priority of the order.')

    maintenance = models.BooleanField(
        default=False,
        help_text='New order is a maintenance order.')

    owner = models.ForeignKey(User,
                              null=False,
                              related_name='owned_orders')

    tab = models.ForeignKey('Tab',
                            null=False,
                            related_name='charged_orders')

    time_created = models.DateTimeField(auto_now_add=True)

    @property
    def first_few_updates(self):
        return self.updates.order_by('time_created')[:10]

    @property
    def earliest_update(self):
        return self.updates.earliest('time_created')

    @property
    def latest_update(self):
        return self.updates.latest('time_created')

    @property
    def time_last_updated(self):
        return self.latest_update.time_created

    @property
    def fulfillment_time(self):
        fulfillment_updates = self.updates.filter(
            new_status=self.STATUS_FULFILLED)
        if fulfillment_updates.exists():
            return fulfillment_updates.latest(
                'time_created').time_created

        return None

    @property
    def number_of_ejection_notices(self):
        fulfillment_time = self.fulfillment_time
        return self.number_of_ejection_notices_since_time(fulfillment_time)

    def number_of_ejection_notices_since_time(self, time):
        if not time:
            return 0
        return self.updates.exclude(
            time_created__lt=time).exclude(
                time_limit_notice=False).count()

    @property
    def last_ejection_notice_time(self):
        ejection_notices_order_updates = \
            self.updates.exclude(time_limit_notice=False)

        if ejection_notices_order_updates.exists():
            return ejection_notices_order_updates.latest(
                'time_created').time_created
        return None

    @property
    def last_extension_time(self):
        all_time_limit_updates = self.updates.exclude(
            time_limit_delta=timedelta())
        return all_time_limit_updates.latest('id').time_created

    @memoize(timeout=timedelta(hours=6).total_seconds())
    def time_limit_as_of_update(self, order_update):
        """Calculate time_limit as of the specified update.

        This is memoized because it can become expensive if an order
        accumulates many many updates. By memoizing with a given update as
        a parameter, we ensure that the time_limit property below will
        always get a fresh result if there has been a newer update. This is
        important for driving the timing of ejection, notices, etc.

        Similar to the technique described in rkelery.SynchronizedTask, we
        use the update ID instead of timestamp because the ID is guaranteed
        monotonically increasing. This avoids potential bugs / ambiguity of
        calculating different totals if two updates are very close together.

        Since order updates are immutable, there's no chance of a memoized
        value becoming incorrect after time passes so we could theoretically
        keep them in the cache forever. However, we'd rather give the cache
        better hints about what can expire and be evicted to make room for
        other entries, especially since all our use cases only really care to
        get the value as of the latest update.

        Theoreticaly we could also get cute and implement these aggregations
        recursively to basically achieve dynamic programming. However, that's
        not expected to be any benefit since all our use cases only care about
        the value of the latest update, so it's not worth the complexity / risk
        of a corrupt cache entry that silently makes the computation incorrect.
        Dynamic programming would also create a lot more entries in the cache
        which take up space that would be better used for other entries.
        """
        all_time_limit_updates = self.updates.exclude(
            time_limit_delta=timedelta())
        considered_time_limit_updates = all_time_limit_updates.filter(
            id__lte=order_update.id)

        log.debug(
            ('Computing time limit for %s ' % self) +
            ('up to the point of update %s. ' % order_update) +
            ('This covers %d updates and may be expensive.' %
             considered_time_limit_updates.count()))
        time_limit = timedelta()
        for update in considered_time_limit_updates:
            time_limit += update.time_limit_delta

        return time_limit

    @property
    def time_limit(self):
        """Get the current time limit (as of the latest update)."""
        all_time_limit_updates = self.updates.exclude(
            time_limit_delta=timedelta())
        return self.time_limit_as_of_update(
            all_time_limit_updates.latest('id'))

    @property
    def ejection_time(self):
        fulfillment_time = self.fulfillment_time

        if fulfillment_time:
            return self.fulfillment_time + self.time_limit
        return None

    @memoize(timeout=timedelta(hours=6).total_seconds())
    def expiration_time_limit_as_of_update(self, order_update):
        """Calculate expiration time limit as of the specified update.

        See description in time_limit_as_of_update for the same technique
        being applied here.
        """
        all_expiration_time_limit_updates = self.updates.exclude(
            expiration_time_limit_delta=timedelta())
        considered_expiration_time_limit_updates = (
            all_expiration_time_limit_updates.filter(id__lte=order_update.id))

        log.debug(
            ('Computing expiration time limit for %s ' % self) +
            ('up to the point of update %s. ' % order_update) +
            ('This covers %d updates and may be expensive.' %
             considered_expiration_time_limit_updates.count()))
        expiration_time_limit = timedelta()
        for update in considered_expiration_time_limit_updates:
            expiration_time_limit += update.expiration_time_limit_delta
        return expiration_time_limit

    @property
    def expiration_time_limit(self):
        all_expiration_time_limit_updates = self.updates.exclude(
            expiration_time_limit_delta=timedelta())
        return self.expiration_time_limit_as_of_update(
            all_expiration_time_limit_updates.latest('id'))

    @property
    def expiration_time(self):
        return self.time_created + self.expiration_time_limit

    @property
    def fulfilled_items(self):
        item_fulfillments = ItemFulfillment.objects.filter(
            order_update__order=self)
        items_dict = OrderedDict()
        for item_fulfillment in sorted(item_fulfillments,
                                       key=attrgetter('nickname')):
            items_dict[item_fulfillment.nickname] = item_fulfillment.item
        return items_dict

    # TODO(stefan): This only supports adding items to the order.
    # Needs to be changed when we support deleting items as an update
    # When (or maybe if) we ever support adding items after an order is placed,
    # this computation running through all updates may become slow and need
    # memoization treatment similar to time_limit above.
    @property
    def items(self):
        items_delta_order_updates = self.updates.exclude(
            items_delta="").order_by('time_created')

        items_dict = OrderedDict()
        for order_update in items_delta_order_updates:
            items = yaml.safe_load(order_update.items_delta)
            for key in items:
                items_dict[key] = items[key]

        return items_dict

    @property
    def changed_item_state_to_maintenance(self):
        # Items cannot be added to the maintenance order after it is created
        return self.updates.filter(maintenance=True).exists()


class OrderUpdate(BaseModel):

    # The creator of an OrderUpdate can differ from the creator
    # of an Order. For auditability, we want to track who created
    # each OrderUpdate and the time they did it at.
    creator_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=False, blank=True)
    creator_object_id = models.PositiveIntegerField(null=False, blank=True)
    creator = GenericForeignKey(
        'creator_content_type', 'creator_object_id')

    comment = models.TextField(
        blank=True,
        default="",
        null=False,
        help_text='')

    expiration_time_limit_delta = models.DurationField(
        default=timedelta(),
        null=False,
        help_text='Timedelta (Format: [DD] [HH:[MM:]]ss[.uuuuuu]) to extend '
                  'the current expiration limit.')

    # Item(s) that we are requesting in JSON format for the order
    items_delta = models.TextField(
        blank=True,
        default="",
        null=False,
        help_text='Items to add to the order.')

    # OrderUpdate was used to set items to maintenance state
    maintenance = models.BooleanField(default=False)

    new_owner = models.ForeignKey(
        User,
        null=True)

    new_status = models.CharField(
        default="",
        blank=True,
        max_length=16,
        choices=Order.STATUS_CHOICES,
        help_text='Order status, one of %s' %
                  repr([choice[0] for choice in Order.STATUS_CHOICES]))

    # Order that will be updated
    order = models.ForeignKey(Order,
                              null=False,
                              related_name='updates',
                              help_text='ID of Order object to update')

    time_limit_delta = models.DurationField(
        default=timedelta(),
        null=False,
        help_text='Timedelta (Format: [DD] [HH:[MM:]]ss[.uuuuuu]) to extend '
                  'the current lease')

    time_created = models.DateTimeField(auto_now_add=True)

    # OrderUpdate was used to notify the user of impending ejection
    time_limit_notice = models.BooleanField(default=False)


class Seed(BaseModel):
    """Generic class representing the source for individual Farm Items."""

    @property
    def name(self):
        raise NotImplementedError('Subclass must override name property.')


class Stockroom(BaseModel):
    """Generic class representing source for physical Items.

    This is the 'Farm' equivalent for ad-hoc items that are
    more static.
    """

    location = models.ForeignKey('Location',
                                 on_delete=models.CASCADE,
                                 null=False,
                                 help_text='Location of the stockroom')


class Tab(BaseModel):
    """A Tab belonging to a User used to calculate fulfillment priority."""

    DEFAULT_LIMIT = 1.0

    # The limit is relative to other tabs' limits.
    limit = models.FloatField(null=False, blank=False)

    owner = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              null=False,
                              related_name='tabs')
