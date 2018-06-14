"""Initializing BodegaCLI setup."""

import argparse
import logging
import pipes
import sys
from enum import Enum
import requests
from bodega_close import BodegaClose
from bodega_consume import BodegaConsume
from bodega_customize import BodegaCustomize
from bodega_describe import BodegaDescribe
from bodega_extend import BodegaExtend
from bodega_list import BodegaList
from bodega_place import BodegaPlace
from bodega_produce import BodegaProduce
from bodega_raw import BodegaRaw
from bodega_transfer import BodegaTransfer
from bodega_utils import Utils

try:
    from toolbox import __version__
except ImportError:
    __version__ = '0000.00.00~dev'


log = logging.getLogger(__name__)


class Commands(Enum):
    """Values COMMAND can take."""

    DESCRIBE = 'describe'
    PLACE = 'place'
    CONSUME = 'consume'
    CLOSE = 'close'
    EXTEND = 'extend'
    TRANSFER = 'transfer'
    RAW = 'raw'
    LIST = 'list'
    CUSTOMIZE = 'customize'
    PRODUCE = 'produce'


class BodegaCLI(object):
    """Parser for the `bodega` CLI.

    The usual command syntax for this CLI is
    `bodega COMMAND TYPE [POSITIONAL_ARGUMENT] [--NAMED_ARGUMENTs ..]`, where:

    - COMMAND is the command name,
    - TYPE is the resource or method type on which COMMAND is to be executed,
    - POSITIONAL_ARGUMENT is (conditioned to COMMAND) a positional argument
      which usually is the identifier for TYPE,
    - NAMED_ARGUMENTs are one or more named arguments which can be
      passed to tweak the functionality of COMMAND. A named argument may take
      value as an input (--named_arg_with_value=VALUE), or it may be a binary
      named argument (--binary_named_arg).
    """

    def __init__(self, bodega_commands):
        """Initialize BodegaCLI using supported list of commands."""
        self.commands = bodega_commands

        description = """Bodega CLI version %s""" % __version__
        self.parser = argparse.ArgumentParser(description=description,
                                              epilog=Utils.epilog)

        self.subparsers = self.parser.add_subparsers()
        self._init_subparsers()

    def _init_subparsers(self):
        self._init_describe()
        self._init_place()
        self._init_consume()
        self._init_close()
        self._init_extend()
        self._init_transfer()
        self._init_raw()
        self._init_list()
        self._init_customize()
        self._init_produce()

    def _init_describe(self):
        description = """Describe an item"""
        sub_parser = self.subparsers.add_parser(Commands.DESCRIBE.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_describe = BodegaDescribe(sub_parser, self.commands)

    def _init_place(self):
        description = """Place an order"""
        sub_parser = self.subparsers.add_parser(Commands.PLACE.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_place = BodegaPlace(sub_parser, self.commands)

    def _init_consume(self):
        description = """Consume an order"""
        sub_parser = self.subparsers.add_parser(Commands.CONSUME.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_consume = BodegaConsume(sub_parser, self.commands)

    def _init_close(self):
        description = """Close an order"""
        sub_parser = self.subparsers.add_parser(Commands.CLOSE.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_close = BodegaClose(sub_parser, self.commands)

    def _init_extend(self):
        description = """Extend time limit of an order"""
        sub_parser = self.subparsers.add_parser(Commands.EXTEND.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_extend = BodegaExtend(sub_parser, self.commands)

    def _init_transfer(self):
        description = """Transfer ownership of an order"""
        sub_parser = self.subparsers.add_parser(Commands.TRANSFER.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_transfer = BodegaTransfer(sub_parser, self.commands)

    def _init_raw(self):
        description = """Make a custom HTTP request to the server"""
        sub_parser = self.subparsers.add_parser(Commands.RAW.value,
                                                description=description,
                                                epilog=Utils.epilog)

        self.bodega_raw = BodegaRaw(sub_parser, self.commands)

    def _init_list(self):
        description = """List items of a given type"""
        sub_parser = self.subparsers.add_parser(Commands.LIST.value,
                                                description=description,
                                                epilog=Utils.epilog)
        self.bodega_list = BodegaList(sub_parser, self.commands)

    def _init_customize(self):
        description = """Customize a dev machine"""
        sub_parser = self.subparsers.add_parser(Commands.CUSTOMIZE.value,
                                                description=description,
                                                epilog=Utils.epilog)
        self.bodega_customize = BodegaCustomize(sub_parser, self.commands)

    def _init_produce(self):
        description = """Produce and customize a dev machine"""
        sub_parser = self.subparsers.add_parser(Commands.PRODUCE.value,
                                                description=description,
                                                epilog=Utils.epilog)
        self.bodega_produce = BodegaProduce(sub_parser, self.commands)

    def parse_and_execute(self):
        args = self.parser.parse_args()
        args_dict = vars(args)
        cli_input = " ".join(pipes.quote(arg) for arg in sys.argv)
        args_dict.update({'cli_input': cli_input})

        try:
            args.func(args_dict)
        except requests.exceptions.HTTPError as e:
            if 400 <= e.response.status_code < 500:
                log.error('User or client error: %s' % e.response.text)
        finally:
            log.debug('Got HTTP Error response from Bodega',
                      exc_info=True)


def main():
    from bodega_commands import BodegaCommands
    from logging_utils import init_logging

    init_logging()
    requests.packages.urllib3.disable_warnings()

    commands = BodegaCommands()

    bodega_cli = BodegaCLI(commands)
    bodega_cli.parse_and_execute()
