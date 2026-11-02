# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mappers to aid in rendering of console output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import RemoteToSMetadata

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path
    from typing import Final

    from ..models import LocalToSMetadata


NULL_CHAR: Final = "[dim]-"


def timestamp_mapping(timestamp: datetime) -> str:
    """Map the UTC metadata timestamp to a localized human-readable string."""
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def accepted_mapping(metadata: RemoteToSMetadata | LocalToSMetadata) -> str:
    """Map the metadata acceptance status to a human-readable string."""
    if isinstance(metadata, RemoteToSMetadata):
        return NULL_CHAR

    tos_accepted = metadata.tos_accepted
    acceptance_timestamp = metadata.acceptance_timestamp
    if tos_accepted:
        if acceptance_timestamp:
            # convert timestamp to localized time
            return f"[bold green]{timestamp_mapping(acceptance_timestamp)}"
        else:
            # accepted but no timestamp
            return "[dim]unknown"
    else:
        return "[bold red]rejected"


def location_mapping(path: Path | None) -> str:
    """Map the metadata path to a human-readable string."""
    if not path:
        return NULL_CHAR
    return str(path.parent.parent)


def version_mapping(version: datetime, remote: RemoteToSMetadata | None) -> str:
    """Map the metadata version to a human-readable string."""
    version_str = timestamp_mapping(version)
    return f"[bold yellow]{version_str} *" if remote else version_str
