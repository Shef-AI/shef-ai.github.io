# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level conda plugin registration."""

from __future__ import annotations

from datetime import timedelta
from functools import cache
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.helpers import add_parser_prefix, add_parser_verbose
from conda.common.configuration import PrimitiveParameter
from conda.common.constants import NULL
from conda.plugins import hookimpl
from conda.plugins.types import (
    CondaPreCommand,
    CondaRequestHeader,
    CondaSetting,
    CondaSubcommand,
)
from rich.console import Console

from . import APP_NAME, APP_VERSION
from .api import CI, get_channels
from .console import (
    noop_printer,
    render_accept,
    render_clean,
    render_info,
    render_interactive,
    render_list,
    render_reject,
    render_view,
)
from .exceptions import CondaToSMissingError
from .local import get_local_metadata
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT
from .remote import ENDPOINT

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Callable, Iterator


#: Default metadata storage location.
DEFAULT_TOS_ROOT = USER_TOS_ROOT

#: Default cache timeout in seconds.
DEFAULT_CACHE_TIMEOUT = timedelta(hours=1).total_seconds()

#: Field separator for request header
FIELD_SEPARATOR = ";"

#: Key-value separator for request header
KEY_SEPARATOR = "="

#: Terms of Service acceptance request header
TOS_ACCEPT_HEADER = "Anaconda-ToS-Accept"

#: Hosts to which the Terms of Service header is added
HOSTS = {"repo.anaconda.com"}


def _add_channel(parser: ArgumentParser) -> None:
    channel_group = parser.add_argument_group("Channel Customization")
    channel_group.add_argument(
        "-c",
        "--channel",
        action="append",
        help="Additional channels to search for Terms of Service.",
    )
    channel_group.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not search default or .condarc channels. Requires --channel.",
    )


def _add_location(parser: ArgumentParser) -> None:
    location_group = parser.add_argument_group("Local Metadata Storage Location")
    location_mutex = location_group.add_mutually_exclusive_group()
    for flag, value, text in (
        ("--site", SITE_TOS_ROOT, "System-wide storage location."),
        ("--system", SYSTEM_TOS_ROOT, "Conda installation storage location."),
        ("--user", USER_TOS_ROOT, "User storage location."),
        ("--env", ENV_TOS_ROOT, "Conda environment storage location."),
    ):
        location_mutex.add_argument(
            flag,
            dest="tos_root",
            action="store_const",
            const=value,
            help=text,
        )
    location_mutex.add_argument(
        "--tos-root",
        action="store",
        help="Custom storage location.",
    )
    parser.set_defaults(tos_root=DEFAULT_TOS_ROOT)


def _add_cache(parser: ArgumentParser) -> None:
    cache_group = parser.add_argument_group("Cache Control")
    cache_mutex = cache_group.add_mutually_exclusive_group()
    cache_mutex.add_argument(
        "--cache-timeout",
        action="store",
        type=int,
        help="Cache timeout (in seconds) to check for Terms of Service updates.",
    )
    cache_mutex.add_argument(
        "--ignore-cache",
        dest="cache_timeout",
        action="store_const",
        const=0,
        help="Ignore the cache and always check for Terms of Service updates.",
    )
    parser.set_defaults(cache_timeout=DEFAULT_CACHE_TIMEOUT)


def _add_json(parser: ArgumentParser) -> None:
    # TODO: replace with conda.cli.helpers.add_parser_json
    parser.add_argument(
        "--json",
        action="store_true",
        default=NULL,
        help="Report all output as json. Suitable for using conda programmatically.",
    )


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    # conda tos --version
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
        help=f"Show the {APP_NAME} version number and exit.",
    )

    # conda tos (default behavior)
    _add_channel(parser)
    add_parser_prefix(parser)
    _add_cache(parser)
    _add_json(parser)
    add_parser_verbose(parser)
    parser.set_defaults(tos_root=DEFAULT_TOS_ROOT)

    # conda tos <COMMAND>
    subparsers = parser.add_subparsers(
        title="subcommand",
        description="The following subcommands are available.",
        dest="cmd",
        required=False,
    )

    # conda tos accept
    accept_parser = subparsers.add_parser(
        "accept",
        help=(
            "Accept the Terms of Service for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(accept_parser)
    add_parser_prefix(accept_parser)
    _add_location(accept_parser)
    _add_cache(accept_parser)
    _add_json(accept_parser)

    # conda tos reject
    reject_parser = subparsers.add_parser(
        "reject",
        help=(
            "Reject the Terms of Service for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(reject_parser)
    add_parser_prefix(reject_parser)
    _add_location(reject_parser)
    _add_cache(reject_parser)
    _add_json(reject_parser)

    # conda tos view
    view_parser = subparsers.add_parser(
        "view",
        help=(
            "View the Terms of Service for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(view_parser)
    add_parser_prefix(view_parser)
    _add_location(view_parser)
    _add_cache(view_parser)
    _add_json(view_parser)

    # conda tos interactive
    interactive_parser = subparsers.add_parser(
        "interactive",
        help=(
            "Interactively accept/reject/view Terms of Service for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(interactive_parser)
    add_parser_prefix(interactive_parser)
    _add_location(interactive_parser)
    _add_cache(interactive_parser)
    _add_json(interactive_parser)
    add_parser_verbose(interactive_parser)

    # conda tos info
    info_parser = subparsers.add_parser(
        "info",
        help=(
            "Display information about the plugin "
            "(e.g., search path and cache directory)."
        ),
    )
    _add_json(info_parser)

    # conda tos clean
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean the cache directories.",
    )
    clean_parser.add_argument(
        "--cache",
        action="store_true",
        help="Remove all cache files.",
    )
    clean_parser.add_argument(
        "--tos",
        action="store_true",
        help="Remove all acceptances/rejections.",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Invoke both `--cache` and `--tos`.",
    )
    _add_json(clean_parser)


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    try:
        # FUTURE: update once we only support conda 25.5+
        from conda.core.prefix_data import PrefixData

        PrefixData(context.target_prefix).assert_exists()
    except AttributeError:
        # AttributeError: PrefixData.assert_exists isn't defined
        from pathlib import Path

        from conda.exceptions import EnvironmentLocationNotFound

        if not (prefix := Path(context.target_prefix).exists()):
            raise EnvironmentLocationNotFound(prefix) from None

    console = Console()
    action: Callable
    kwargs = {}
    if args.cmd == "accept":
        action = render_accept
    elif args.cmd == "reject":
        action = render_reject
    elif args.cmd == "view":
        action = render_view
    elif args.cmd == "interactive":
        action = render_interactive
        kwargs["auto_accept_tos"] = context.plugins.auto_accept_tos
        kwargs["always_yes"] = context.always_yes
        kwargs["verbose"] = context.verbose
    elif args.cmd == "info":
        # refactor into `conda info` plugin (when possible)
        return render_info(json=context.json, console=console)
    elif args.cmd == "clean":
        # refactor into `conda clean` plugin (when possible)
        return render_clean(
            cache=args.cache,
            tos=args.tos,
            all=args.all,
            tos_root=args.tos_root,
            json=context.json,
            console=console,
        )
    else:
        # default
        action = render_list
        kwargs["verbose"] = context.verbose

    return action(
        *context.channels,
        tos_root=args.tos_root,
        cache_timeout=args.cache_timeout,
        json=context.json,
        console=console,
        **kwargs,
    )


@hookimpl
def conda_subcommands() -> Iterator[CondaSubcommand]:
    """Return a list of subcommands for the plugin."""
    yield CondaSubcommand(
        name="tos",
        action=execute,
        summary=(
            "A subcommand for viewing, accepting, rejecting, and otherwise interacting "
            "with a channel's Terms of Service (ToS). This plugin periodically checks "
            "for updated Terms of Service for the active/selected channels. "
            "Channels with a Terms of Service will need to be accepted or rejected "
            "prior to use. Conda will only allow package installation from channels "
            "without a Terms of Service or with an accepted Terms of Service. "
            "Attempting to use a channel with a rejected Terms of Service will result "
            "in an error."
        ),
        configure_parser=configure_parser,
    )


@hookimpl
def conda_settings() -> Iterator[CondaSetting]:
    """Return a list of settings for the plugin."""
    yield CondaSetting(
        name="auto_accept_tos",
        description="Automatically accept Terms of Service (ToS) for all channels.",
        parameter=PrimitiveParameter(False, element_type=bool),
    )


def _pre_command_check_tos(_command: str) -> None:
    render_interactive(
        *context.channels,
        tos_root=DEFAULT_TOS_ROOT,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
        json=context.json,
        verbose=context.verbose,
        auto_accept_tos=context.plugins.auto_accept_tos,
        always_yes=context.always_yes,
        json_printer=noop_printer,  # no JSON output even if --json
    )


@hookimpl(tryfirst=True)
def conda_pre_commands() -> Iterator[CondaPreCommand]:
    """Return a list of pre-commands for the plugin."""
    yield CondaPreCommand(
        name="check_tos",
        action=_pre_command_check_tos,
        run_for={
            "create",
            "env_create",
            "env_remove",
            "env_update",
            "install",
            "remove",
            "rename",
            "search",
            "update",
        },
    )


@cache
def _get_tos_acceptance_header() -> str:
    values = []
    for channel in get_channels(*context.channels):
        try:
            local_pair = get_local_metadata(
                channel,
                extend_search_path=[DEFAULT_TOS_ROOT],
            )
        except CondaToSMissingError:
            pass
        else:
            values.append(
                KEY_SEPARATOR.join(
                    (
                        channel.base_url,
                        str(int(local_pair.metadata.version.timestamp())),
                        "accepted" if local_pair.metadata.tos_accepted else "rejected",
                        str(int(local_pair.metadata.acceptance_timestamp.timestamp())),
                    )
                )
            )
    if CI:
        values.append("CI=true")
    return FIELD_SEPARATOR.join(values)


@hookimpl
def conda_request_headers(host: str, path: str) -> Iterator[CondaRequestHeader]:
    """Return a list of request headers for the plugin."""
    if (
        # only add the header to anaconda.com endpoints
        host in HOSTS
        # only add the Terms of Service header for non-Terms of Service endpoints
        and not path.endswith(f"/{ENDPOINT}")
    ):
        yield CondaRequestHeader(
            name=TOS_ACCEPT_HEADER,
            value=_get_tos_acceptance_header(),
        )
