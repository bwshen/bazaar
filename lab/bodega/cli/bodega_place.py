"""Bodega PLACE command."""

from argparse import FileType
from enum import Enum
import yaml
from bodega_utils import OutputFormats
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in PLACE command."""

    ORDER = 'order'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for PLACE ORDER command."""

    REQUIREMENTS = 'requirements'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for PLACE ORDER command."""

    NO_WAIT = 'no_wait'
    COMMENT = 'comment'
    MAINTENANCE_ORDER = 'maintenance_order'
    OUTPUT_FORMAT = 'output_format'
    TIME = 'time'

    FILE = 'file'


class OrderTypes(Enum):
    """Values TYPE can take in PLACE ORDER command."""

    RKTEST_YML = 'rktest_yml'
    SD_DEV_MACHINE = 'sd_dev_machine'


class BodegaPlace(object):
    """Sub-parser for the PLACE command."""

    def __init__(self, sub_parser, bodega_commands):
        """Create a BodegaPlace object using parser and bodega_commands obj."""
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_place_order()

    def _init_place_order(self):
        description = """Place an order"""
        sub_parser = self.subparsers.add_parser(Types.ORDER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.NO_WAIT.value),
            Utils.get_long_arg_from_name(NamedArguments.NO_WAIT.value),
            action='store_true', required=False, default=False,
            help='Skip blocking wait for the order to be fulfilled')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.COMMENT.value),
            Utils.get_long_arg_from_name(NamedArguments.COMMENT.value),
            type=str, required=False, default=None,
            help='Comment on the order request')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.MAINTENANCE_ORDER.value),
            Utils.get_long_arg_from_name(
                NamedArguments.MAINTENANCE_ORDER.value),
            required=False, action='store_true',
            help='Make the order a maintenance order')
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

        sub_parser.add_argument(PositionalArguments.REQUIREMENTS.value,
                                type=str, nargs='*',
                                help='Specify requirements for order inline')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.FILE.value),
            Utils.get_long_arg_from_name(NamedArguments.FILE.value),
            type=FileType('r'), required=False, default=None,
            help='Specify requirements for order in a YAML file')

        sub_parser.set_defaults(func=self._exec_place_order)

    def _exec_place_order(self, args_dict):
        cli_input = args_dict['cli_input']
        comment = args_dict[NamedArguments.COMMENT.value]
        is_maintenance_order = \
            args_dict[NamedArguments.MAINTENANCE_ORDER.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]
        no_wait = args_dict[NamedArguments.NO_WAIT.value]
        time_limit = args_dict[NamedArguments.TIME.value]

        if args_dict[NamedArguments.FILE.value]:
            if len(args_dict[PositionalArguments.REQUIREMENTS.value]) > 0:
                raise Exception("""Order requirements specified in
                both inline fashion and input file.""")

            file = args_dict[NamedArguments.FILE.value]
            # Replace tabs with spaces as yaml doesn't allow them
            order_items = yaml.safe_load(file.read().replace('\t', '    '))
        else:
            if len(args_dict[PositionalArguments.REQUIREMENTS.value]) == 0:
                raise Exception("""No order requirements specified.""")

            order_items = {}
            requirement_strings = \
                args_dict[PositionalArguments.REQUIREMENTS.value]
            auto_generated_nickname_count = 0
            for requirement_string in requirement_strings:
                item_nickname, item_type, requirements = Utils.\
                    parse_bodega_item_requirement_values(requirement_string)

                if not item_type:
                    raise Exception(
                        """No bodega item type defined in %s.
                        Make sure you follow the format
                        `[NICK_NAME:]BODEGA_TYPE(REQ1=VAL1,REQ2=VAL2,..)`."""
                        % requirement_string)

                if not item_nickname:
                    auto_generated_nickname_count += 1
                    item_nickname = '_item_%d' % auto_generated_nickname_count

                if item_nickname in order_items:
                    raise Exception('Multiple orders with nickname %s'
                                    % item_nickname)

                order_items[item_nickname] = {
                    "type": item_type,
                    "requirements": requirements
                }

        (order_sid, fulfilled_items) = self.commands.place_order(
            order_items, cli_input, no_wait=no_wait,
            is_maintenance_order=is_maintenance_order, time_limit=time_limit,
            comment=comment)

        if not no_wait:
            fulfilled_items = Utils.get_specified_format_from_dict(
                fulfilled_items, output_format)
            print 'Fulfilled items for the order %s:\n %s' % (order_sid,
                                                              fulfilled_items)
        else:
            print 'Placed order %s but not waiting for the order to be ' \
                  'fulfilled. You may need to call consume command before ' \
                  'you can start working with the fulfilled items.' \
                  % (order_sid)
