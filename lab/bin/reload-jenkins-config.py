#!/usr/bin/env python

import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'dev'))
import logging_utils

log = logging.getLogger(os.path.basename(__name__))

sys.path.append(os.path.join(SDMAIN_ROOT, 'src', 'scripts', 'jenkins'))

from jenkins_helpers import RkLabJenkins


if __name__ == '__main__':
    logging_utils.init_logging()

    jenkins = RkLabJenkins()

    log.info('Reloading Jenkins configuration from disk.')
    jenkins.reload_config()
