"""Bodega Produce CLI class."""
from enum import Enum
from bodega_utils import OutputFormats, Utils


class Types(Enum):
    """Values TYPE can take in PRODUCE command."""

    DEV_MACHINE = 'dev_machine'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for PRODUCE command."""

    REQUIREMENTS = 'requirements'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for PRODUCE command."""

    COMMENT = 'comment'
    OUTPUT_FORMAT = 'output_format'
    SD_DEV_MOUNTRC_FILE = 'sd_dev_mountrc_file'
    TIME = 'time'
    GIT_REPO_FILE = "git_repo_file"


class BodegaProduce(object):
    """Sub-parser for the PRODUCE command."""

    def __init__(self, sub_parser, bodega_commands):
        """Initialize BodegaProduce class."""
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_dev_machine()

    def _init_dev_machine(self):
        description = """Obtain and configure a new dev machine"""
        sub_parser = self.subparsers.add_parser(Types.DEV_MACHINE.value,
                                                description=description,
                                                epilog=Utils.epilog)
        sub_parser.add_argument(PositionalArguments.REQUIREMENTS.value,
                                nargs='*',
                                help="List of requirements for dev machine, " +
                                "'<param1>=<value1> <param2>=<value2>'")

        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.SD_DEV_MOUNTRC_FILE.value),
            Utils.get_long_arg_from_name(
                NamedArguments.SD_DEV_MOUNTRC_FILE.value),
            default=Utils.get_default_sd_dev_file(),
            help='sd_dev_mountrc file to use [default:%(default)s]',
            metavar='FILE')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.COMMENT.value),
            Utils.get_long_arg_from_name(NamedArguments.COMMENT.value),
            type=str, required=False, default=None,
            help='Comment on the order request')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.YAML.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to YAML')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.TIME.value),
            Utils.get_long_arg_from_name(NamedArguments.TIME.value),
            type=Utils.parse_time, required=False, default=None,
            help='Time limit for the place order eg: 30m, 2h, 1d, 1d2h30m')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.GIT_REPO_FILE.value),
            Utils.get_long_arg_from_name(
                NamedArguments.GIT_REPO_FILE.value),
            default=None,
            help='git repo file to use, " + \
            "refer to conf/sd_dev_git_repos.defaults',
            metavar='YML FILE')
        sub_parser.set_defaults(func=self._exec_new_dev_machine)

    def _exec_new_dev_machine(self, args_dict):
        cli_input = args_dict['cli_input']
        requirements = args_dict[PositionalArguments.REQUIREMENTS.value]
        sync_file = args_dict[NamedArguments.SD_DEV_MOUNTRC_FILE.value]
        time_limit = args_dict[NamedArguments.TIME.value]
        comment = args_dict[NamedArguments.COMMENT.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]
        git_repo_file = args_dict[NamedArguments.GIT_REPO_FILE.value]
        requirements_dict = {}
        order_item = {}
        for req in requirements:
            key, val = [_.strip() for _ in req.split('=')]
            try:
                val = int(val)
            except ValueError:
                pass
            requirements_dict[key] = val
        order_item['_item_1'] = {
            "type": 'sd_dev_machine',
            "requirements": requirements_dict
        }
        order_sid, item = self.commands.place_order(order_item,
                                                    cli_input, no_wait=False,
                                                    is_maintenance_order=False,
                                                    time_limit=time_limit,
                                                    comment=comment)
        username = item['_item_1']["username"]
        ip_addr = item['_item_1']["ip_address"]
        password = item['_item_1']["password"]
        item = Utils.get_specified_format_from_dict(item, output_format)
        print 'Fulfilled items for the order %s:\n %s' % (order_sid, item)
        self.commands.configure_dev_machine(username, ip_addr,
                                            sync_file=sync_file,
                                            git_repo_file=git_repo_file,
                                            password=password)
