# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from conda.exceptions import ArgumentError
from rich.console import Console
from rich.table import Table

from ..api import (
    CI,
    JUPYTER,
    accept_tos,
    clean_cache,
    clean_tos,
    get_all_tos,
    get_channels,
    get_one_tos,
    reject_tos,
)
from ..exceptions import (
    CondaToSMissingError,
    CondaToSNonInteractiveError,
    CondaToSRejectedError,
)
from ..path import CACHE_DIR, SEARCH_PATH
from .mappers import NULL_CHAR, accepted_mapping, location_mapping, version_mapping
from .prompt import FuzzyPrompt

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterable
    from typing import Any, Final

    from conda.models.channel import Channel

    from ..models import LocalPair, RemotePair

    AcceptedType = dict[str, dict]
    RejectedType = list[Channel]
    NonInteractiveType = list[Channel]
    ChannelPairsType = list[tuple[Channel, RemotePair | LocalPair]]

try:
    from conda.common.terminal import is_interactive_tty
except ImportError:
    try:
        from conda.common.terminal import is_tty

        IS_INTERACTIVE = (
            is_tty() and hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
        )
    except ImportError:
        from conda.common.io import IS_INTERACTIVE  # type: ignore[no-redef]
else:
    IS_INTERACTIVE = is_interactive_tty()

TOS_OUTDATED: Final = "* Terms of Service version(s) are outdated."

TOS_AUTO_ACCEPTED_TEMPLATE: Final = (
    "By accessing {channel} with auto acceptance enabled (auto_accept_tos=True) "
    "for this repository you acknowledge and agree to the Terms of Service:\n"
    "{tos_text}"
)
TOS_CI_ACCEPTED_TEMPLATE: Final = (
    "By accessing {channel} via CI "
    "for this repository you acknowledge and agree to the Terms of Service:\n"
    "{tos_text}"
)


def noop_printer(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """Use this no-op printer when nothing should be printed to the screen."""


def printable(func: Callable[..., int]) -> Callable[..., int]:
    """Pass console and printer functions to the decorated function.

    This instantiates a console for the render functions if not provided and
    the console and json printers to pass them to the decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> int:  # noqa: ANN401
        console = kwargs.pop("console", Console())
        json = kwargs.pop("json", False)
        printer = kwargs.pop("printer", noop_printer if json else console.print)
        json_printer = kwargs.pop("json_printer", console.print_json)
        return func(
            *args,
            **kwargs,
            json=json,
            console=console,
            printer=printer,
            json_printer=json_printer,
        )

    return wrapper


@printable
def render_list(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    json: bool = False,
    verbose: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Display listing of unaccepted, accepted, and rejected Terms of Service."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Support")
    if verbose:
        table.add_column("Location")
        add_row = table.add_row
    else:
        add_row = lambda *args: table.add_row(*args[:-1])  # noqa: E731

    json_output: dict[str, Any] = {}
    outdated = False
    for channel, metadata_pair in get_all_tos(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
        if not metadata_pair:
            json_output[channel.base_url] = None
            add_row(channel.base_url, NULL_CHAR, NULL_CHAR, NULL_CHAR, NULL_CHAR)
        else:
            json_output[channel.base_url] = {
                **metadata_pair.metadata.model_dump(mode="json"),
                "outdated": bool(metadata_pair.remote),
                "path": str(metadata_pair.path),
            }
            outdated = outdated or bool(metadata_pair.remote)
            add_row(
                channel.base_url,
                version_mapping(metadata_pair.metadata.version, metadata_pair.remote),
                accepted_mapping(metadata_pair.metadata),
                metadata_pair.metadata.support,
                location_mapping(metadata_pair.path),
            )

    if json:
        json_printer(data=json_output)
    else:
        printer(table)
        if outdated:
            printer(f"[bold yellow]{TOS_OUTDATED}")
    return 0


@printable
def render_view(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    json: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Display the Terms of Service text for the given channels."""
    json_output: dict[str, Any] = {}
    for channel in get_channels(*channels):
        try:
            metadata = get_one_tos(
                channel,
                tos_root=tos_root,
                cache_timeout=cache_timeout,
            ).metadata
        except CondaToSMissingError:
            json_output[channel.base_url] = None
            printer(f"no Terms of Service for {channel}")
        else:
            json_output[channel.base_url] = metadata.model_dump(mode="json")
            printer(f"viewing Terms of Service for {channel}:")
            printer(metadata.text)

    if json:
        json_printer(data=json_output)
    return 0


@printable
def render_accept(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    json: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Display acceptance of the Terms of Service for the given channels."""
    json_output: dict[str, Any] = {}
    for channel in get_channels(*channels):
        try:
            metadata = accept_tos(
                channel,
                tos_root=tos_root,
                cache_timeout=cache_timeout,
            ).metadata
        except CondaToSMissingError:
            json_output[channel.base_url] = None
            printer(f"Terms of Service not found for {channel}")
        else:
            json_output[channel.base_url] = metadata.model_dump(mode="json")
            printer(f"accepted Terms of Service for {channel}")

    if json:
        json_printer(data=json_output)
    return 0


@printable
def render_reject(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    json: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Display rejection of the Terms of Service for the given channels."""
    json_output: dict[str, Any] = {}
    for channel in get_channels(*channels):
        try:
            metadata = reject_tos(
                channel,
                tos_root=tos_root,
                cache_timeout=cache_timeout,
            ).metadata
        except CondaToSMissingError:
            json_output[channel.base_url] = None
            printer(f"Terms of Service not found for {channel}")
        else:
            json_output[channel.base_url] = metadata.model_dump(mode="json")
            printer(f"rejected Terms of Service for {channel}")

    if json:
        json_printer(data=json_output)
    return 0


def _prompt_acceptance(
    channel: Channel,
    pair: RemotePair | LocalPair,
    console: Console,
    choices: Iterable[str] = ("(a)ccept", "(r)eject", "(v)iew"),
) -> bool:
    prologue = ""
    if pair.remote:
        state = "[bold red]rejected[/]"
        if pair.metadata.tos_accepted:
            state = "[bold green]accepted[/]"
        prologue = (
            f"The Terms of Service for {channel} was previously {state}. "
            f"An updated Terms of Service is now available.\n"
        )

    response = FuzzyPrompt.ask(
        f"{prologue}Do you accept the Terms of Service (ToS) for {channel}?",
        choices=choices,
        console=console,
    )
    if response == "accept":
        return True
    elif response == "reject":
        return False
    else:
        console.print(pair.latest_text)
        return _prompt_acceptance(channel, pair, console, ("(a)ccept", "(r)eject"))


def _gather_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> tuple[
    AcceptedType,
    RejectedType,
    ChannelPairsType,
]:
    accepted = {}
    rejected = []
    channel_pairs = []
    for channel in get_channels(*channels):
        try:
            pair = get_one_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            # CondaToSMissingError: no metadata found
            continue

        if pair.remote or getattr(pair.metadata, "tos_accepted", None) is None:
            # Terms of Service has been updated or
            # Terms of Service haven't been accepted or rejected yet
            channel_pairs.append((channel, pair))
        elif pair.metadata.tos_accepted:
            accepted[channel.base_url] = pair.metadata.model_dump(mode="json")
        else:
            rejected.append(channel)
    return accepted, rejected, channel_pairs


def _is_tos_accepted(
    *,
    channel: Channel,
    pair: RemotePair | LocalPair,
    auto_accept_tos: bool,
    always_yes: bool,
    json_mode: bool,
    console: Console,
    printer: Callable[..., None],
) -> bool:
    """Determine if the Terms of Service is accepted for a channel."""
    # Auto-accept has highest priority
    if auto_accept_tos:
        printer(
            TOS_AUTO_ACCEPTED_TEMPLATE.format(
                channel=channel,
                tos_text=pair.latest_text,
            ),
            style="bold yellow",
        )
        return True

    # CI environment auto-accepts with warning
    if CI:
        printer(
            TOS_CI_ACCEPTED_TEMPLATE.format(
                channel=channel,
                tos_text=pair.latest_text,
            ),
            style="bold yellow",
        )
        return True

    # Non-interactive environments exits before prompt
    if json_mode or always_yes or JUPYTER or not IS_INTERACTIVE:
        raise CondaToSNonInteractiveError

    # Interactive prompt
    return _prompt_acceptance(channel, pair, console)


def _process_channel_pairs(
    *,
    channel_pairs: ChannelPairsType,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    auto_accept_tos: bool,
    always_yes: bool,
    json_mode: bool,
    console: Console,
    printer: Callable[..., None],
    # optional arguments, if provided they are updated in place
    accepted: AcceptedType | None = None,
    rejected: RejectedType | None = None,
    non_interactive: NonInteractiveType | None = None,
) -> tuple[AcceptedType, RejectedType, NonInteractiveType]:
    """Iterate over channel pairs and process the Terms of Service."""
    accepted = {} if accepted is None else accepted
    rejected = [] if rejected is None else rejected
    non_interactive = [] if non_interactive is None else non_interactive

    for channel, pair in channel_pairs:
        try:
            if _is_tos_accepted(
                channel=channel,
                pair=pair,
                auto_accept_tos=auto_accept_tos,
                always_yes=always_yes,
                json_mode=json_mode,
                console=console,
                printer=printer,
            ):
                accepted[channel.base_url] = accept_tos(
                    channel,
                    tos_root=tos_root,
                    cache_timeout=cache_timeout,
                ).metadata
            else:
                reject_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
                rejected.append(channel)
        except CondaToSNonInteractiveError:
            non_interactive.append(channel)

    return accepted, rejected, non_interactive


@printable
def render_interactive(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    json: bool = False,
    verbose: bool = False,
    auto_accept_tos: bool,
    always_yes: bool,
    console: Console | None = None,
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Prompt user to accept or reject Terms of Service for channels."""
    if verbose:
        printer("[bold blue]Gathering channels...")

    accepted, rejected, channel_pairs = _gather_tos(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )

    if verbose:
        printer("[bold yellow]Reviewing channels...")

    # exit early if some channels are already rejected
    if rejected:
        printer(f"[bold red]{len(rejected)} channel Terms of Service rejected")
        raise CondaToSRejectedError(*rejected)

    if CI:
        printer("[bold yellow]CI detected...")
    elif JUPYTER:
        printer("[bold yellow]Jupyter detected...")

    accepted, rejected, non_interactive = _process_channel_pairs(
        accepted=accepted,
        rejected=rejected,
        channel_pairs=channel_pairs,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
        auto_accept_tos=auto_accept_tos,
        always_yes=always_yes,
        json_mode=json,
        console=console,
        printer=printer,
    )

    if non_interactive:
        raise CondaToSNonInteractiveError(*non_interactive)
    elif rejected:
        printer(f"[bold red]{len(rejected)} channel Terms of Service rejected")
        raise CondaToSRejectedError(*rejected)

    if verbose or accepted:
        printer(f"[bold green]{len(accepted)} channel Terms of Service accepted")

    if json:
        json_printer(data=accepted)
    return 0


@printable
def render_info(
    *,
    json: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Display information about the Terms of Service cache."""
    data: dict[str, str | tuple[str, ...]] = {}
    data["SEARCH_PATH"] = SEARCH_PATH
    try:
        relative_dir = Path("~", CACHE_DIR.relative_to(Path.home()))
    except ValueError:
        # ValueError: CACHE_DIR is not relative to the user's home directory
        relative_dir = CACHE_DIR
    data["CACHE_DIR"] = str(relative_dir)

    if json:
        json_printer(data=data)
    else:
        table = Table(show_header=False)
        table.add_column("Key")
        table.add_column("Value")
        for key, value in data.items():
            if isinstance(value, tuple | list):
                value = "\n".join(map(str, value))
            else:
                value = str(value)
            table.add_row(key, value)
        printer(table)
    return 0


@printable
def render_clean(
    cache: bool,
    tos: bool,
    all: bool,  # noqa: A002
    *,
    tos_root: str | os.PathLike[str] | Path,
    json: bool = False,
    console: Console | None = None,  # noqa: ARG001
    printer: Callable[..., None],
    json_printer: Callable[..., None],
) -> int:
    """Clean the metadata cache directories."""
    if not (all or cache or tos):
        raise ArgumentError(
            "At least one removal target must be given. See 'conda tos clean --help'."
        )

    json_output: dict[str, Any] = {}
    if all or cache:
        json_output["cache"] = cache_files = list(map(str, clean_cache()))
        printer(f"Removed {len(cache_files)} cache files.")
    if all or tos:
        json_output["tos"] = tos_files = list(map(str, clean_tos(tos_root)))
        printer(f"Removed {len(tos_files)} Terms of Service files.")

    if json:
        json_printer(data=json_output)
    return 0
