"""Bodega Close CLI class."""
from enum import Enum
from bodega_utils import OutputFormats
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in CLOSE command."""

    ORDER = 'order'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for CLOSE command."""

    ORDER_SID = 'order_sid'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for CLOSE command."""

    COMMENT = 'comment'
    OUTPUT_FORMAT = 'output_format'


class BodegaClose(object):
    """Sub-parser for the CLOSE command."""

    def __init__(self, sub_parser, bodega_commands):
        """Initialize BodegaClose class."""
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_close_order()

    def _init_close_order(self):
        description = """Close an order"""
        sub_parser = self.subparsers.add_parser(Types.ORDER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(PositionalArguments.ORDER_SID.value, type=str,
                                nargs='+', help='SIDs of orders to be closed')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.COMMENT.value),
            Utils.get_long_arg_from_name(NamedArguments.COMMENT.value),
            type=str, required=False, default=None,
            help='Comment on the order closing request')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.YAML.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to YAML')

        sub_parser.set_defaults(func=self._exec_close_order)

    def _exec_close_order(self, args_dict):
        order_sids = args_dict[PositionalArguments.ORDER_SID.value]
        cli_input = args_dict['cli_input']
        comment = args_dict[NamedArguments.COMMENT.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]

        for order_sid in order_sids:
            result = self.commands.close_order(order_sid, cli_input,
                                               comment=comment)

            result = Utils.get_specified_format_from_dict(result,
                                                          output_format)
            print result
