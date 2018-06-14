"""These tests make actual orders on the Bodega infrastructure.

They are not meant to be tested in an automated fashion.
"""

import json
import logging
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # noqa
SCRIPT_NAME = os.path.basename(__file__)  # noqa
SDMAIN_ROOT = \
    os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..'))  # noqa

from bodega_commands import BodegaCommands

log = logging.getLogger(os.path.basename(__name__))


def test_place_order(commands):
    requirements = {
        "nickname_0": {
            "type": "rktest_yml",
            "requirements": {
                "platform": "DYNAPOD"
            }
        },
    }
    order_sid = commands.place_order(requirements)[0]
    assert order_sid
    return order_sid


def test_close_order(commands, order_sid):
    assert commands.close_order(order_sid)


def test_describe_order(commands, order_sid):
    result = json.dumps(commands.describe_order(order_sid), indent=4,
                        sort_keys=True)
    log.info(result)
    assert result


def test_extend_order(commands, order_sid):
    result = json.dumps(commands.extend_order(order_sid), indent=4,
                        sort_keys=True)
    log.info(result)
    assert result


def test_raw_request(commands):
    result = json.dumps(commands.raw_request('GET', '/profile/'), indent=4,
                        sort_keys=True)
    log.info(result)
    assert result


def test_list_orders(commands):
    user_profile = commands.get_current_user_profile()
    result = commands.list_orders(user_email=user_profile['email'],
                                  status='LIVE')
    result = json.dumps(result, indent=4, sort_keys=True)
    log.info(result)
    assert result

if __name__ == '__main__':
    commands = BodegaCommands()

    order_sid = test_place_order(commands)
    test_describe_order(commands, order_sid)
    test_list_orders(commands)
    test_extend_order(commands, order_sid)
    test_close_order(commands, order_sid)
    test_raw_request(commands)
