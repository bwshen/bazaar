#!/usr/bin/env python
import argparse
import json
import logging
import os
import sys
import time
import subprocess
import yaml
import collections
import requests

from datetime import timedelta
from urlparse import urlparse
from datetime import datetime
from operator import attrgetter

import yaml

# disable warning
requests.packages.urllib3.disable_warnings()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # noqa
SCRIPT_NAME = os.path.basename(__file__)  # noqa
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))  # noqa

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'bodega', 'client'))  # noqa
from bodega_client import BodegaClient

from bodega_order import get_order_times
from bodega_order import get_monthly_cost

DEBUG=''

# from bodega_commands import BodegaCommands

def get_queue_length(sid):
  bodega_client = BodegaClient()  
  order  = bodega_client.get('/orders/'+sid)
  order_time = order['time_created'].replace('T',' ').split('.')[0].replace('Z','')
  tab_priority = order['tab_based_priority']

  commands = BodegaCommands()
  queue_length = commands._get_order_queue_length(order_creation_time=order_time, tab_based_priority=tab_priority)
  
  print('sid:'+str(sid)+',queue_length:'+str(queue_length)+',order_time:'+str(order_time)+',pri:'+tab_priority)


def main(sid):
#  (order_time, target_time) = get_order_times(sid)
#  print('order_time:'+str(order_time)+',target_time:'+str(target_time))
#  get_queue_length(sid)
#  get_monthly_cost('cgpmvi-noj8rws')
   print(get_monthly_cost('ondz63-dukw8ey'))
#- timedelta(days=30))
#--------------------------------
main('knaqvh-fszbewe')


