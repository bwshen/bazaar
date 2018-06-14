"""Bodega Custmize CLI class."""
from enum import Enum
from bodega_utils import Utils


class Types(Enum):
    """Values TYPE can take in CUSTOMIZE command."""

    DEV_MACHINE = 'dev_machine'


class PositionalArguments(Enum):
    """POSITIONAL_ARGUMENTs for CUSTOMIZE command."""

    HOST_INFO = 'host_info'


class NamedArguments(Enum):
    """NAMED_ARGUMENTs for CUSTOMIZE command."""

    SD_DEV_MOUNTRC_FILE = 'sd_dev_mountrc_file'
    PEM_FILE = "pem_file"
    GIT_REPO_FILE = "git_repo_file"


class BodegaCustomize(object):
    """Sub-parser for the CUSTOMIZE command."""

    def __init__(self, sub_parser, bodega_commands):
        """Initialize BodegaCustomize class."""
        self.commands = bodega_commands

        self.parser = sub_parser
        self.subparsers = self.parser.add_subparsers()

        self._init_subparsers()

    def _init_subparsers(self):
        self._init_dev_machine()

    def _init_dev_machine(self):
        description = """Configure a existing dev machine"""
        sub_parser = self.subparsers.add_parser(Types.DEV_MACHINE.value,
                                                description=description,
                                                epilog=Utils.epilog)
        sub_parser.add_argument(PositionalArguments.HOST_INFO.value,
                                type=Utils.parse_userhost,
                                help='Host information <user>@<ipaddr>, ' +
                                'username is optional')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.SD_DEV_MOUNTRC_FILE.value),
            Utils.get_long_arg_from_name(
                NamedArguments.SD_DEV_MOUNTRC_FILE.value),
            default=Utils.get_default_sd_dev_file(),
            help='sd_dev_mountrc file to use [default:%(default)s]',
            metavar='FILE')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.PEM_FILE.value),
            Utils.get_long_arg_from_name(
                NamedArguments.PEM_FILE.value),
            default=Utils.get_default_ubuntu_pem_key(),
            help='pem file to use [default:%(default)s]',
            metavar='FILE')
        sub_parser.add_argument(
            Utils.get_short_arg_from_name(
                NamedArguments.GIT_REPO_FILE.value),
            Utils.get_long_arg_from_name(
                NamedArguments.GIT_REPO_FILE.value),
            default=None,
            help='git repo file to use, " + \
            "refer to conf/sd_dev_git_repos.defaults',
            metavar='YML FILE')

        sub_parser.set_defaults(func=self._exec_configure_dev_machine)

    def _exec_configure_dev_machine(self, args_dict):
        username, host = args_dict[PositionalArguments.HOST_INFO.value]
        sync_file = args_dict[NamedArguments.SD_DEV_MOUNTRC_FILE.value]
        pem_file = args_dict[NamedArguments.PEM_FILE.value]
        git_repo_file = args_dict[NamedArguments.GIT_REPO_FILE.value]
        self.commands.configure_dev_machine(username, host,
                                            sync_file=sync_file,
                                            git_repo_file=git_repo_file,
                                            pem_file=pem_file)
