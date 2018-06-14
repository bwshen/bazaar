from enum import Enum
from bodega_utils import OutputFormats
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in TRANSFER command."""

    ORDER = 'order'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for TRANSFER command."""

    ORDER_SID = 'order_sid'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for TRANSFER command."""

    EMAIL = 'email'
    SID = 'sid'
    COMMENT = 'comment'
    OUTPUT_FORMAT = 'output_format'


class BodegaTransfer(object):
    """Sub-parser for the TRANSFER command."""

    def __init__(self, sub_parser, bodega_commands):
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_transfer_order()

    def _init_transfer_order(self):
        description = """Transfer ownership of an order"""
        sub_parser = self.subparsers.add_parser(Types.ORDER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(PositionalArguments.ORDER_SID.value, type=str,
                                help='SID of order to be extended')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.COMMENT.value),
            Utils.get_long_arg_from_name(NamedArguments.COMMENT.value),
            type=str, required=False, default=None,
            help='Comment on the order transfer request')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.YAML.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to YAML')

        group = sub_parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.EMAIL.value),
            Utils.get_long_arg_from_name(NamedArguments.EMAIL.value),
            type=str, required=False, default=None,
            help='Email of new owner')
        group.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.SID.value),
            Utils.get_long_arg_from_name(NamedArguments.SID.value),
            type=str, required=False, default=None,
            help='SID of new owner')

        sub_parser.set_defaults(func=self._exec_transfer_order)

    def _exec_transfer_order(self, args_dict):
        order_sid = args_dict[PositionalArguments.ORDER_SID.value]
        cli_input = args_dict['cli_input']
        comment = args_dict[NamedArguments.COMMENT.value]
        new_owner_email = args_dict[NamedArguments.EMAIL.value]
        new_owner_sid = args_dict[NamedArguments.SID.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]

        result = self.commands.transfer_order(
            order_sid, cli_input, comment=comment, new_owner_sid=new_owner_sid,
            new_owner_email=new_owner_email)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result
