"""Close Orders that have surpass their time limit."""
import logging
from datetime import datetime, timedelta
from django.db import transaction
from instrumentation.utils import instrumentation_context
from pytz import utc

from .models import Order, OrderUpdate

log = logging.getLogger(__name__)
MAINTENANCE_ORDER_NOTICE_INTERVAL = timedelta(hours=96)
TIME_LEFT_NOTIFICATION_SCHEDULE = [timedelta(minutes=15),
                                   timedelta(minutes=30),
                                   timedelta(hours=1),
                                   timedelta(hours=2),
                                   timedelta(hours=4),
                                   timedelta(hours=8),
                                   timedelta(hours=16),
                                   timedelta(hours=24),
                                   timedelta(hours=36),
                                   timedelta(days=3),
                                   timedelta(days=7),
                                   timedelta(days=14),
                                   timedelta(days=30)]
MIN_TIME_DELTA_BEFORE_EJECTION = timedelta(minutes=15)
URGENT_WARNINGS_TIME_LIMIT = timedelta(hours=1)


class EjectionManager(object):
    def __init__(self, order_update_creator):
        """Initialize EjectionManager."""
        self.order_update_creator = order_update_creator

    def _create_ejection_notice_order_update(self,
                                             order,
                                             comment,
                                             new_status="",
                                             time_limit_notice=True):
        return OrderUpdate.objects.create(creator=self.order_update_creator,
                                          order=order,
                                          comment=comment,
                                          new_status=new_status,
                                          time_limit_notice=time_limit_notice)

    def _should_send_maintenance_notice(self,
                                        curr_time,
                                        last_ejection_notice_time):
        if not last_ejection_notice_time:
            return True
        return (curr_time - last_ejection_notice_time >
                MAINTENANCE_ORDER_NOTICE_INTERVAL)

    def _get_order_ejection_notice_comment(self, order, time_left):

        if time_left < URGENT_WARNINGS_TIME_LIMIT:
            comment = '_*`URGENT MESSAGE - IMPENDING ORDER CLOSURE`*_\n'
        else:
            comment = ''
        comment += ("This order is under your name and has %s left "
                    "on its time limit. Please CLOSE the Order if you "
                    "are done with the items. Order will automatically "
                    "be closed at %s.\nTo extend Order, run "
                    "`lab/bin/bodega extend order %s`. To close Order, "
                    "run `lab/bin/bodega close order %s`."
                    % (str(time_left),
                       order.ejection_time.isoformat(),
                       order.sid,
                       order.sid))
        return comment

    def _eject(self, order):
        log.debug('%s has surpassed the time limit so closing'
                  ' the order now.' % order)
        comment = ("This order has been automatically closed for "
                   "going over the time limit of %s which started "
                   "at %s."
                   % (str(order.time_limit),
                      order.fulfillment_time.isoformat()))
        with transaction.atomic():
            self._create_ejection_notice_order_update(
                order=order,
                comment=comment,
                new_status=Order.STATUS_CLOSED,
                time_limit_notice=False)
            order.status = Order.STATUS_CLOSED
            order.save(update_fields=['status'])

    def _send_ejection_notices_or_eject(self, order, curr_time):
        """Send the ejection notices for an order."""
        time_left = order.ejection_time - curr_time
        last_ejection_notice_time = order.last_ejection_notice_time

        if last_ejection_notice_time:
            time_since_last_notice = curr_time - last_ejection_notice_time
        else:
            time_since_last_notice = None

        for delta in TIME_LEFT_NOTIFICATION_SCHEDULE:
            time_at_delta = order.ejection_time - delta
            if time_left > delta:
                log.debug('Time left of %s is greater than the next '
                          'notification time of %s so do nothing.'
                          % (time_left, delta))
                continue
            elif time_left < timedelta() and \
                    time_since_last_notice and \
                    time_since_last_notice >= MIN_TIME_DELTA_BEFORE_EJECTION:
                with instrumentation_context('order_ejections'):
                    self._eject(order)
                    return
            elif order.number_of_ejection_notices_since_time(time_at_delta):
                log.debug('%s has already received a notification after %s'
                          % (order, time_at_delta.isoformat()))
                return
            else:
                log.debug('%s has not received a notification after %s so send'
                          ' one now.'
                          % (order, time_at_delta.isoformat()))
                comment = self._get_order_ejection_notice_comment(order,
                                                                  time_left)
                self._create_ejection_notice_order_update(order, comment)
                return

    def process_order_time_limit(self, order, curr_time):
        number_of_ejection_notices = order.number_of_ejection_notices
        last_ejection_notice_time = order.last_ejection_notice_time
        order_time_limit = order.time_limit
        order_ejection_time = order.ejection_time

        if order.maintenance:
            log.debug('%s is a maintenance Order and will not be ejected '
                      'for going over a time limit.' % order)

            if self._should_send_maintenance_notice(curr_time,
                                                    last_ejection_notice_time):
                comment = ("Notice #%d: This order is under your name and is "
                           "holding items under maintenance. Please CLOSE the "
                           "Order if you are done with the items. To close "
                           "Order, run `lab/bin/bodega close order %s`"
                           % ((number_of_ejection_notices + 1),
                              order.sid))
                self._create_ejection_notice_order_update(order, comment)
            return

        time_left = order.ejection_time - curr_time
        log.debug('%s has a time limit of %s with %s remaining and will be '
                  'auto-closed at %s UTC. Current time for procressing is %s.'
                  % (str(order), str(order_time_limit),
                     str(time_left),
                     order_ejection_time.isoformat(),
                     curr_time.isoformat()))
        if number_of_ejection_notices:
            log.debug('%s has %d ejection notices with the last '
                      'one occuring at %s.'
                      % (str(order),
                         number_of_ejection_notices,
                         last_ejection_notice_time.isoformat()))
        else:
            log.debug('%s has received no ejection notices so far.'
                      % str(order))
        self._send_ejection_notices_or_eject(order, curr_time)

    def process_orders_time_limits(self):
        non_closed_orders = Order.objects.filter(
            status=Order.STATUS_FULFILLED)

        for order in non_closed_orders:
            curr_time = datetime.now(utc)
            self.process_order_time_limit(order, curr_time)
