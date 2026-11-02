from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from functools import partial

    from .. import APP_NAME, APP_VERSION
    from .main_install import HELP as INSTALL_HELP
    from .main_install import configure_parser as configure_parser_install
    from .main_remove import HELP as REMOVE_HELP
    from .main_remove import configure_parser as configure_parser_remove
    from .main_reset import HELP as RESET_HELP
    from .main_reset import configure_parser as configure_parser_reset
    from .main_update import HELP as UPDATE_HELP
    from .main_update import configure_parser as configure_parser_update

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
        help=f"Show the '{APP_NAME}' version number and exit.",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
    )

    configure_parser_install(subparsers.add_parser("install", help=INSTALL_HELP))
    configure_parser_remove(subparsers.add_parser("remove", help=REMOVE_HELP))
    configure_parser_reset(subparsers.add_parser("reset", help=RESET_HELP))
    configure_parser_update(subparsers.add_parser("update", help=UPDATE_HELP))
    parser.set_defaults(func=partial(parser.parse_args, ["--help"]))


def execute(args: argparse.Namespace) -> int:
    return args.func(args)
