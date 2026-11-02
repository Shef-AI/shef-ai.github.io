# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError
from conda.models.channel import Channel

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Self


class CondaToSError(CondaError):
    """Base exception."""


class CondaToSMissingError(CondaToSError):
    """Error class for when the metadata is missing for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(f"No Terms of Service for {_url(channel)}.")


class CondaToSInvalidError(CondaToSMissingError):
    """Error class for when the metadata is invalid for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(f"Invalid Terms of Service for {_url(channel)}.")


class CondaToSPermissionError(PermissionError, CondaToSError):
    """Error class for when the metadata file cannot be written."""

    def __init__(
        self: Self,
        path: str | os.PathLike[str] | Path,
        channel: str | Channel | None = None,
    ) -> None:
        """Format error message with channel base URL and path."""
        addendum = f" for {_url(channel)}" if channel else ""
        super().__init__(
            f"Unable to read/write path ({path}){addendum}. Please check permissions."
        )


class CondaToSRejectedError(CondaToSError):
    """Error class for when the Terms of Service are rejected for a channel."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        channel_urls = [_url(channel) for channel in channels]
        accept_commands = [
            f"conda tos accept --override-channels --channel {url}"
            for url in channel_urls
        ]

        super().__init__(
            f"Terms of Service has been rejected for the following channels. "
            f"Please remove or accept them before proceeding:\n"
            f"{_bullet(channel_urls)}\n"
            f"\n"
            f"To accept these channels' Terms of Service, run the following commands:\n"
            f"{_bullet(accept_commands, prefix='    ')}\n"
            f"\n"
            f"{_get_removal_guidance()}"
        )


class CondaToSNonInteractiveError(CondaToSError):
    """Error class when Terms of Service are not actionable in non-interactive mode."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        channel_urls = [_url(channel) for channel in channels]
        accept_commands = [
            f"conda tos accept --override-channels --channel {url}"
            for url in channel_urls
        ]

        super().__init__(
            f"Terms of Service have not been accepted for the following channels. "
            f"Please accept or remove them before proceeding:\n"
            f"{_bullet(channel_urls)}\n"
            f"\n"
            f"To accept these channels' Terms of Service, run the following commands:\n"
            f"{_bullet(accept_commands, prefix='    ')}\n"
            f"\n"
            f"{_get_removal_guidance()}"
        )


def _url(channel: str | Channel) -> str:
    _channel = channel if isinstance(channel, Channel) else Channel(str(channel))
    return str(_channel.base_url or channel)


def _bullet(args: Iterable[str], *, prefix: str = "    - ") -> str:
    return prefix + f"\n{prefix}".join(args)


def _get_removal_guidance() -> str:
    """Generate removal guidance based on channel types."""
    return (
        "For information on safely removing channels from your conda configuration,\n"
        "please see the official documentation:\n\n"
        "    https://www.anaconda.com/docs/tools/working-with-conda/channels"
    )
