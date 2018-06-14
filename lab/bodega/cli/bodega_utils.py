"""Common methods and static objects to be shared across the module."""

import csv
import json
import logging
import re
import StringIO
from argparse import ArgumentTypeError
from datetime import timedelta
from enum import Enum
from getpass import getuser
from os import pardir, path
import yaml

log = logging.getLogger(__name__)

SCRIPT_DIR = path.dirname(path.abspath(__file__))
SCRIPT_NAME = path.basename(__file__)
SDMAIN_ROOT = path.abspath(path.join(SCRIPT_DIR, *([pardir] * 3)))

ON_PREM_LOCATIONS = ['COLO', 'HQ']


class Utils:
    epilog = """As a rule of thumb, all arguments must be accurately defined.
    The utility may silently fail or display default results for erroneous
    inputs."""

    @classmethod
    def _validate_ipv4(cls, host):
        """Validate IP string for IPv4 format."""
        try:
            parts = host.split('.')
            return len(parts) == 4 and \
                all([int(p) >= 0 and int(p) < 256 for p in parts])
        except:
            return False

    @classmethod
    def parse_userhost(cls, inp):
        """Parser to validate the host information."""
        if '@' in inp:
            user, host = inp.split('@')
        else:
            user, host = getuser(), inp

        # TODO: In future we have to support domain names and IPv6
        if not cls._validate_ipv4(host):
            msg = """'%s' is not valid IPv4.""" % inp
            raise ArgumentTypeError(msg)
        return user, host

    @classmethod
    def parse_time(cls, inp):
        """Parser function to convert duration(string) to timedelta object."""
        duration_regex = re.compile(r'^'
                                    r'((?P<days>\d+?)d)?'
                                    r'((?P<hours>\d+?)h)?'
                                    r'((?P<minutes>\d+?)m)?'
                                    r'((?P<seconds>\d+?)s)?'
                                    r'$')
        values = duration_regex.match(inp)
        if not values:
            msg = """'%s' doesn\'t satisfy the input format for duration.
            It should be a number followed by one of suffixes `m`, `h`
            or `d`, e.g. 30m, 3h, 1d, 1d4h30m""" % inp
            raise ArgumentTypeError(msg)
        params = {}
        for key, value in values.groupdict().iteritems():
            if value:
                params[key] = int(value)
        duration = timedelta(**params)
        if duration == timedelta():
            msg = """Time value can not represent zero duration.
            The input value received for duration: '%s'
            Valid values: 1d, 4h, 30m, 4h30m, 1d10h10m""" % inp
            raise ArgumentTypeError(msg)
        return duration

    @classmethod
    def get_default_sd_dev_file(cls):
        sd_dev = path.join(path.expanduser('~'), '.sd_dev_mountrc')
        if not path.isfile(sd_dev):
            sd_dev = path.join(SDMAIN_ROOT, 'conf', 'sd_dev_mountrc.defaults')
        return sd_dev

    @classmethod
    def get_default_ubuntu_pem_key(cls):
        return path.join(SDMAIN_ROOT, 'deployment/ssh_keys/ubuntu.pem')

    @classmethod
    def get_values_from_enum(cls, enum):
        """Convert an enum into a list of its values."""
        return [member.value for member in enum]

    @classmethod
    def get_short_arg_from_name(cls, name):
        """Get short argument for a named argument: `type` becomes `-t`."""
        return '-%s' % name[0]

    @classmethod
    def get_long_arg_from_name(cls, name):
        """Get long argument for a named argument: `type` becomes `--type`."""
        return '--%s' % name

    @classmethod
    def get_required_keys_for_item(cls, item, verbosity_level):
        keys = {}

        keys[(BodegaEntityTypes.ORDERS.value,
              VerbosityLevels.LOW.value)] \
            = [u'sid', u'status', u'time_created', u'ejection_time']
        keys[(BodegaEntityTypes.ORDERS.value,
              VerbosityLevels.MEDIUM.value)] \
            = [u'sid', u'status', u'items_json', u'time_created',
               u'ejection_time']
        keys[(BodegaEntityTypes.ORDERS.value,
              VerbosityLevels.HIGH.value)] \
            = None

        keys[(BodegaEntityTypes.RKTEST_YMLS.value,
              VerbosityLevels.LOW.value)] \
            = [u'sid', u'name', u'location', u'platform']
        keys[(BodegaEntityTypes.RKTEST_YMLS.value,
              VerbosityLevels.MEDIUM.value)] \
            = [u'sid', u'name', u'state', u'location', u'platform']
        keys[(BodegaEntityTypes.RKTEST_YMLS.value,
              VerbosityLevels.HIGH.value)] \
            = None

        keys[(BodegaEntityTypes.SD_DEV_MACHINES.value,
              VerbosityLevels.LOW.value)] \
            = [u'sid', u'location', u'ip_address', u'version']
        keys[(BodegaEntityTypes.SD_DEV_MACHINES.value,
              VerbosityLevels.MEDIUM.value)] \
            = [u'sid', u'location', u'ip_address', u'version', u'model',
               u'privileged_mode']
        keys[(BodegaEntityTypes.SD_DEV_MACHINES.value,
              VerbosityLevels.HIGH.value)] \
            = None

        keys[(BodegaEntityTypes.USERS.value,
              VerbosityLevels.LOW.value)] \
            = [u'sid', u'username']
        keys[(BodegaEntityTypes.USERS.value,
              VerbosityLevels.MEDIUM.value)] \
            = [u'sid', u'username', u'email']
        keys[(BodegaEntityTypes.USERS.value,
              VerbosityLevels.HIGH.value)] \
            = None

        keys[(BodegaEntityTypes.TASKS.value,
              VerbosityLevels.LOW.value)] \
            = [u'id', u'display_type', u'state', u'time_published']
        keys[(BodegaEntityTypes.TASKS.value,
              VerbosityLevels.MEDIUM.value)] \
            = [u'id', u'display_type', u'state', u'time_published',
               u'time_ready', u'wall_time']
        keys[(BodegaEntityTypes.TASKS.value,
              VerbosityLevels.HIGH.value)] \
            = None

        if not (item, verbosity_level) in keys:
            raise NotImplementedException(
                'Item %s with verbosity %s not supported yet' %
                (item, verbosity_level))
        return keys[(item, verbosity_level)]

    @classmethod
    def get_json_from_dict(cls, inp):
        return json.dumps(inp, indent=4, sort_keys=True)

    @classmethod
    def get_yaml_from_dict(cls, inp):
        # Hack to convert nested OrderedDict to dict
        inp = json.loads(json.dumps(inp))
        return yaml.safe_dump(inp, default_flow_style=False)

    @classmethod
    def get_tsv_from_dict(cls, inp):
        # Wrap singletons in list
        if type(inp) != list:
            inp = [inp]
        if len(inp) > 0:
            si = StringIO.StringIO()
            dw = csv.DictWriter(si, fieldnames=inp[0].keys(), delimiter='\t')
            dw.writeheader()
            dw.writerows(inp)
            result = si.getvalue()
            si.close()
        else:
            result = ''
        return result

    @classmethod
    def get_specified_format_from_dict(cls, inp, format=None):
        if not format:
            format = OutputFormats.YAML.value
        if format == OutputFormats.JSON.value:
            result = cls.get_json_from_dict(inp)
        elif format == OutputFormats.YAML.value:
            result = cls.get_yaml_from_dict(inp)
        elif format == OutputFormats.TSV.value:
            result = cls.get_tsv_from_dict(inp)
        else:
            raise NotImplementedException(
                'Conversion of dict to %s not supported yet' % format)
        return result

    @classmethod
    def parse_bodega_item_requirement_values(cls, inp):
        """Unwrap a string of the following form.

        `[NICK_NAME:BODEGA_TYPE](REQUIREMENT=VALUE*)` to get bodega item
        requirements
        """
        # Using regex for parsing assumes that none of the characters
        # [':', '(', ')', '=', ','] can be part of tokens for this piece of
        # code to work.
        # TODO (satwant.rana): Use a proper parsing framework to avoid regex

        match = re.match(r"((?P<nick_name>[^:]+):)?(?P<bodega_type>[^\(]+)?" +
                         r"\((?P<rest>[^\)]*)\)", inp)
        if not match:
            raise Exception("""Can\'t parse %s into bodega item and it\'s
            requirements. Make sure you follow the format
            `[[NICK_NAME:]BODEGA_TYPE](REQ1=VAL1,REQ2=VAL2,..)`.""" % inp)

        nick_name = match.group('nick_name')
        if nick_name:
            nick_name = nick_name.strip()

        bodega_type = match.group('bodega_type')
        if bodega_type:
            bodega_type = bodega_type.strip()

        requirement_dict = {}
        rest = match.group('rest')

        if rest != "":
            key_vals = [t.split('=') for t in rest.split(',')]
            for t in key_vals:
                key = t[0].strip()
                value = t[1].strip()
                log.debug('Checking if value %s for key %s is an integer.'
                          % (key, value))
                try:
                    value = int(value)
                except ValueError:
                    pass
                requirement_dict[key] = value

        if ('location' in requirement_dict) and \
                ('network' not in requirement_dict) and \
                requirement_dict['location'] in ON_PREM_LOCATIONS:
            log.debug('Location was specified but not network. Adding '
                      '"network=native" to the requirements dict since the '
                      'chosen location %s is one of %s.'
                      % (requirement_dict['location'], ON_PREM_LOCATIONS))
            requirement_dict['network'] = 'native'

        return nick_name, bodega_type, requirement_dict


class NotImplementedException(Exception):
    pass


class OutputFormats(Enum):
    """Values OUTPUT_FORMAT can take."""

    YAML = 'yaml'
    JSON = 'json'
    TSV = 'tsv'


class VerbosityLevels(Enum):
    """Values VERBOSITY can take."""

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class BodegaEntityTypes(Enum):
    """Values TYPE can take in LIST command."""

    ORDERS = 'orders'
    RKTEST_YMLS = 'rktest_ymls'
    SD_DEV_MACHINES = 'sd_dev_machines'
    USERS = 'users'
    TASKS = 'tasks'
