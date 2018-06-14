from enum import Enum
from bodega_utils import OutputFormats
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in RAW command."""

    METHOD = 'method'


class Methods(Enum):
    """Values METHOD can take in RAW command."""

    GET = 'get'
    POST = 'post'
    PUT = 'put'
    DELETE = 'delete'
    OPTIONS = 'options'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for RAW command."""

    URL = 'url'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for RAW command."""

    PARAMS = 'params'
    DATA = 'data'
    OUTPUT_FORMAT = 'output_format'


class BodegaRaw(object):
    """Sub-parser for the RAW command."""

    def __init__(self, sub_parser, bodega_commands):
        self.commands = bodega_commands

        self.parser = sub_parser

        self.parser.add_argument(Types.METHOD.value, type=str,
                                 choices=Utils.get_values_from_enum(Methods),
                                 help='HTTP method of the request.')
        self.parser.add_argument(PositionalArguments.URL.value, type=str,
                                 help='relative uri of the request.')

        self.parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.PARAMS.value),
            Utils.get_long_arg_from_name(NamedArguments.PARAMS.value),
            type=str, required=False, default=None,
            help='Specify params to form query string of the url.')
        self.parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.DATA.value),
            Utils.get_long_arg_from_name(NamedArguments.DATA.value),
            type=str, required=False, default=None,
            help='Specify data to pass values in HTTP request\'s body.')
        self.parser.add_argument(
            Utils.get_short_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            Utils.get_long_arg_from_name(NamedArguments.OUTPUT_FORMAT.value),
            type=str, required=False, default=OutputFormats.JSON.value,
            choices=Utils.get_values_from_enum(OutputFormats),
            help='Choose output format, defaults to JSON.')

        self.parser.set_defaults(func=self._exec_raw_request)

    def _exec_raw_request(self, args_dict):
        method = args_dict[Types.METHOD.value]
        url = args_dict[PositionalArguments.URL.value]
        params = args_dict[NamedArguments.PARAMS.value]
        data = args_dict[NamedArguments.DATA.value]
        output_format = args_dict[NamedArguments.OUTPUT_FORMAT.value]

        result = self.commands.raw_request(method, url, params=params,
                                           data=data)

        result = Utils.get_specified_format_from_dict(result, output_format)
        print result
