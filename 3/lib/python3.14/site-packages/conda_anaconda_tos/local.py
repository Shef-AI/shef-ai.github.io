# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Low-level local (acceptance & rejection) Terms of Service metadata management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.models.channel import Channel
from pydantic import ValidationError

from .exceptions import CondaToSMissingError, CondaToSPermissionError
from .models import LocalPair, LocalToSMetadata, RemoteToSMetadata
from .path import get_all_channel_paths, get_channel_paths, get_metadata_path, get_path

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import Any


def write_metadata(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
    metadata: LocalToSMetadata | RemoteToSMetadata,
    # kwargs extends/overrides metadata fields
    **kwargs: Any,  # noqa: ANN401
) -> LocalPair:
    """Write the metadata to file."""
    # argument validation/coercion
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("`channel` must have a base URL.")
    if not isinstance(metadata, LocalToSMetadata | RemoteToSMetadata):
        raise TypeError("`metadata` must be a LocalToSMetadata or RemoteToSMetadata.")

    # create/update ToSMetadata object
    metadata = LocalToSMetadata(
        **{
            **metadata.model_dump(),
            **kwargs,
            # override the following fields with the current time and channel base URL
            "acceptance_timestamp": datetime.now(tz=timezone.utc),
            "base_url": channel.base_url,
        }
    )

    # write metadata to file
    path = get_metadata_path(tos_root, channel, metadata.version)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(metadata.model_dump_json())
    except PermissionError as exc:
        # PermissionError: can't write metadata path
        raise CondaToSPermissionError(path, channel) from exc

    return LocalPair(metadata=metadata, path=path)


def read_metadata(path: str | os.PathLike[str] | Path) -> LocalPair | None:
    """Load the metadata from file."""
    try:
        return LocalPair(
            metadata=LocalToSMetadata.model_validate_json(get_path(path).read_text()),
            path=path,
        )
    except (FileNotFoundError, ValidationError):
        # FileNotFoundError: metadata path doesn't exist
        # ValidationError: invalid JSON schema, treat it as missing
        return None
    except PermissionError as exc:
        # PermissionError: can't read metadata path
        raise CondaToSPermissionError(path) from exc


def get_local_metadata(
    channel: str | Channel,
    *,
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> LocalPair:
    """Get the latest metadata for the given channel."""
    # find all metadata files for the given channel
    metadata_pairs = [
        metadata_pair
        for path in get_channel_paths(channel, extend_search_path=extend_search_path)
        if (metadata_pair := read_metadata(path))
    ]

    # return if no metadata found
    if not metadata_pairs:
        raise CondaToSMissingError(f"No Terms of Service metadata found for {channel}")

    # reverse to order from lowest to highest priority
    metadata_pairs.reverse()

    # return newest (and highest priority) metadata for channel
    return sorted(metadata_pairs)[-1]


def get_local_metadatas(
    *,
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[tuple[Channel, LocalPair]]:
    """Yield all metadata."""
    # group metadata by channel
    grouped_metadatas: dict[Channel, list[LocalPair]] = {}
    for path in get_all_channel_paths(extend_search_path=extend_search_path):
        if metadata_pair := read_metadata(path):
            channel = Channel(metadata_pair.metadata.base_url)
            grouped_metadatas.setdefault(channel, []).append(metadata_pair)

    # return the newest (and highest priority) metadata for each channel
    for channel, metadata_pairs in grouped_metadatas.items():
        # reverse to order from lowest to highest priority
        metadata_pairs.reverse()

        # yield newest (and highest priority) metadata for channel
        yield channel, sorted(metadata_pairs)[-1]
