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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # noqa
SCRIPT_NAME = os.path.basename(__file__)  # noqa
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))  # noqa

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'bodega', 'client'))  # noqa
from bodega_client import BodegaClient

from bodega_order import get_order_times

DEBUG='1'

# disable warning
requests.packages.urllib3.disable_warnings()

def main(sid):
  (order_time, target_time) = get_order_times(sid)

  print('order_time:'+str(order_time)+',target_time:'+str(target_time))


#--------------------------------
main('knaqvh-fszbewe')


