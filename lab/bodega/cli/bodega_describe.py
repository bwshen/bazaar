from enum import Enum
from bodega_utils import BodegaEntityTypes
from bodega_utils import OutputFormats
from bodega_utils import Utils
from bodega_utils import VerbosityLevels


class Types(Enum):
    """Values TYPE can take in DESCRIBE command."""

    ORDER = 'order'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for DESCRIBE command."""

    ORDER_SID = 'order_sid'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for DESCRIBE command."""

    OUTPUT_FORMAT = 'output_format'
    VERBOSITY = 'verbosity'


class BodegaDescribe(object):
    """Sub-parser for the DESCRIBE command."""

    def __init__(self, sub_parser, bodega_commands):
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_describe_order()

    def _init_describe_order(self):
        description = """Describe an order"""
        sub_parser = self.subparsers.add_parser(Types.ORDER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(PositionalArguments.ORDER_SID.value, type=str,
                                help='SID of order to be described.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.YAML.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to YAML.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.VERBOSITY.value),
            Utils.get_long_arg_from_name(NamedArguments.VERBOSITY.value),
            type=str, required=False, default=VerbosityLevels.LOW.value,
            choices=Utils.get_values_from_enum(VerbosityLevels),
            help='Choose output verbosity.')

        sub_parser.set_defaults(func=self._exec_describe_order)

    def _exec_describe_order(self, args_dict):
        order_sid = args_dict[PositionalArguments.ORDER_SID.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]
        verbosity = args_dict[NamedArguments.VERBOSITY.value]

        required_keys = Utils.get_required_keys_for_item(
            BodegaEntityTypes.ORDERS.value, verbosity)
        result = self.commands.describe_order(order_sid,
                                              required_keys=required_keys)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result
