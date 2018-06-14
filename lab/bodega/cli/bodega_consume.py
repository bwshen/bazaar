from enum import Enum
from bodega_utils import OutputFormats
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in CONSUME command."""

    ORDER = 'order'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for CONSUME command."""

    ORDER_SID = 'order_sid'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for CONSUME command."""

    OUTPUT_FORMAT = 'output_format'


class BodegaConsume(object):
    """Sub-parser for the CONSUME command."""

    def __init__(self, sub_parser, bodega_commands):
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_consume_order()

    def _init_consume_order(self):
        description = """Consume an order with an rktest_yml item"""
        sub_parser = self.subparsers.add_parser(Types.ORDER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(PositionalArguments.ORDER_SID.value, type=str,
                                help='SID of order to be consumed.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.YAML.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to YAML.')

        sub_parser.set_defaults(func=self._exec_consume_order)

    def _exec_consume_order(self, args_dict):
        order_sid = args_dict[PositionalArguments.ORDER_SID.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]

        result = self.commands.consume_order(order_sid)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result
