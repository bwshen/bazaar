from enum import Enum
from bodega_utils import BodegaEntityTypes
from bodega_utils import OutputFormats
from bodega_utils import Utils
from bodega_utils import VerbosityLevels


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for LIST ORDERS command."""

    OUTPUT_FORMAT = 'output_format'
    COUNT = 'count'

    # NAMED_ARGUMENTs specific for LIST ORDERS command
    ALL = 'all'
    EMAIL = 'email'
    STATUS = 'status'
    VERBOSITY = 'verbosity'

    # NAMED_ARGUMENTs for LIST TYPE command, where TYPE can be any of the Types
    # except ORDERS
    PARAMS = 'params'


class OrderStatuses(Enum):
    """Values STATUS can take in LIST ORDERS command."""

    OPEN = 'OPEN'
    FULFILLED = 'FULFILLED'
    CLOSED = 'CLOSED'
    LIVE = 'LIVE'


class BodegaList(object):
    """Sub-parser for the LIST command."""

    def __init__(self, sub_parser, bodega_commands):
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers(dest='subparser_name')

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_list_orders()
        self._init_list_types()

    def _init_list_orders(self):
        description = """List orders"""
        sub_parser = self.subparsers.add_parser(BodegaEntityTypes.ORDERS.value,
                                                description=description,
                                                epilog=Utils.epilog)

        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.STATUS.value),
            Utils.get_long_arg_from_name(NamedArguments.STATUS.value),
            type=str, required=False, default=OrderStatuses.LIVE.value,
            choices=Utils.get_values_from_enum(OrderStatuses),
            help='List orders with given status, defaults to LIVE.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.TSV.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to TSV.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.VERBOSITY.value),
            Utils.get_long_arg_from_name(NamedArguments.VERBOSITY.value),
            type=str, required=False, default=VerbosityLevels.LOW.value,
            choices=Utils.get_values_from_enum(VerbosityLevels),
            help='Choose output verbosity.')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.COUNT.value),
            Utils.get_long_arg_from_name(NamedArguments.COUNT.value),
            type=int, required=False, default=1000,
            help='Limit number of orders to be listed, defaults to 1000.')

        group = sub_parser.add_mutually_exclusive_group()
        group.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.EMAIL.value),
            Utils.get_long_arg_from_name(NamedArguments.EMAIL.value),
            type=str, required=False, default=None,
            help='List orders identified by a user\'s email')
        group.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.ALL.value),
            Utils.get_long_arg_from_name(NamedArguments.ALL.value),
            required=False, action='store_true',
            help='List orders of all users.')

        sub_parser.set_defaults(func=self._exec_list_orders)

    def _init_list_types(self):
        types = list(BodegaEntityTypes)
        types.remove(BodegaEntityTypes.ORDERS)
        for type in types:
            description = """List %s""" % type.value
            sub_parser = self.subparsers.add_parser(type.value,
                                                    description=description,
                                                    epilog=Utils.epilog)

            sub_parser.add_argument(
                Utils.get_short_arg_from_name(NamedArguments.PARAMS.value),
                Utils.get_long_arg_from_name(NamedArguments.PARAMS.value),
                required=False, default=None,
                help='Params used to form query string.')
            sub_parser.add_argument(
                Utils.get_short_arg_from_name(
                    NamedArguments.OUTPUT_FORMAT.value),
                Utils.get_long_arg_from_name(
                    NamedArguments.OUTPUT_FORMAT.value),
                type=str, required=False, default=OutputFormats.TSV.value,
                choices=Utils.get_values_from_enum(OutputFormats),
                help='Choose output format, defaults to TSV.')
            sub_parser.add_argument(
                Utils.get_short_arg_from_name(NamedArguments.VERBOSITY.value),
                Utils.get_long_arg_from_name(NamedArguments.VERBOSITY.value),
                type=str, required=False, default=VerbosityLevels.LOW.value,
                choices=Utils.get_values_from_enum(VerbosityLevels),
                help='Choose output verbosity.')
            sub_parser.add_argument(
                Utils.get_short_arg_from_name(NamedArguments.COUNT.value),
                Utils.get_long_arg_from_name(NamedArguments.COUNT.value),
                type=int, required=False, default=1000,
                help='Limit number of items to be listed, defaults to 1000.')

            sub_parser.set_defaults(func=self._exec_list_types)

    def _exec_list_orders(self, args_dict):
        email = args_dict[NamedArguments.EMAIL.value]
        all = args_dict[NamedArguments.ALL.value]
        status = args_dict[NamedArguments.STATUS.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]
        verbosity = args_dict[NamedArguments.VERBOSITY.value]
        count = args_dict[NamedArguments.COUNT.value]

        required_keys = Utils.get_required_keys_for_item(
            BodegaEntityTypes.ORDERS.value, verbosity)

        if all:
            result = self.commands.list_orders(status=status,
                                               required_keys=required_keys,
                                               max_count=count)
        else:
            if not email:
                email = self.commands.get_current_user_profile()['email']
            result = self.commands.list_orders(user_email=email, status=status,
                                               required_keys=required_keys,
                                               max_count=count)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result

    def _exec_list_types(self, args_dict):
        type = args_dict['subparser_name']
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]
        count = args_dict[NamedArguments.COUNT.value]
        verbosity = args_dict[NamedArguments.VERBOSITY.value]

        params = args_dict[NamedArguments.PARAMS.value]
        if params:
            _, _, params = Utils.parse_bodega_item_requirement_values(params)

        required_keys = Utils.get_required_keys_for_item(type, verbosity)
        type_relative_uri = '/%s/' % type
        result = self.commands.list(item_relative_uri=type_relative_uri,
                                    params=params, max_count=count,
                                    required_keys=required_keys)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result
