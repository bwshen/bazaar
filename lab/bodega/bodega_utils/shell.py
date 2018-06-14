"""Shell utility functions for Bodega."""
import logging
import subprocess
from bodega_core.exceptions import bodega_error

log = logging.getLogger(__name__)


def send_local_command(cmd):
    log.info('Running command "%s" locally.' % cmd)

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    log.debug(stdout)

    if process.returncode != 0:
        error_msg = ('Received non-zero return code %s from subprocess. '
                     'stderr: %s'
                     % (stderr.strip(), process.returncode))
        bodega_error(log, error_msg)
    log.debug('Ran command "%s" locally successfully with no errors.' % cmd)
