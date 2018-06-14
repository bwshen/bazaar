#!/usr/bin/env python

"""Reserve a pod through Bodega interface."""
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

DEBUG = '1'
SAMPLE_SIZE=20
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # noqa
SCRIPT_NAME = os.path.basename(__file__)  # noqa
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))  # noqa

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'bodega', 'client'))  # noqa
from bodega_client import BodegaClient

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'lib'))  # noqa
from logging_init import init_logging

# from pre_build import fetch_testbed_resource_yamls

log = logging.getLogger(os.path.basename(__name__))

# disable warning
requests.packages.urllib3.disable_warnings()

from bodega_order import get_mean_order_time
from bodega_order import get_order_times

def main():

  begin_time = datetime.now()
  platform = 'DYNAPOD'
  avg_dynapod = get_mean_order_time(platform,SAMPLE_SIZE)
  platform = 'PROD_BRIK'
  avg_prodbrik = get_mean_order_time(platform,SAMPLE_SIZE)

  if (DEBUG):
     print('avergge wait time for DYNAPOD:'+str(avg_dynapod))
     print('avergge wait time for PROD_BRIK:'+str(avg_prodbrik))

# num = get_mean_order_time('PROD_BRIK',SAMPLE_SIZE)

  end_time = datetime.now()
  duration = end_time - begin_time
  if (DEBUG):
    print('duration:'+str(duration.seconds)+' seconds')


  data = dict(
    dynapod = avg_dynapod,
    prod_brik = avg_prodbrik
   )

  with open('/tmp/order-time.yml', 'w') as outfile:
    yaml.dump(data, outfile, default_flow_style=False)

#--------------------------

main()
