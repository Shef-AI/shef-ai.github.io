# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Models to encapsulate Terms of Service metadata."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 # needed for Pydantic model
from pathlib import Path  # noqa: TC003 # needed for Pydantic model
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from typing import Self


class _ToSMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    version: datetime
    text: str
    support: str

    def __ge__(self: Self, other: _ToSMetadata) -> bool:
        """Compare the ToS metadata version."""
        if not isinstance(other, _ToSMetadata):
            return NotImplemented
        return self.version >= other.version


class RemoteToSMetadata(_ToSMetadata):
    """Metadata schema for the remote endpoint."""


class LocalToSMetadata(_ToSMetadata):
    """Metadata schema with acceptance fields."""

    base_url: str
    tos_accepted: bool
    acceptance_timestamp: datetime


class _MetadataPathPair(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: _ToSMetadata
    # FUTURE: Python 3.10+, switch to `Path | None`
    path: Optional[Path]  # noqa: UP045
    # FUTURE: Python 3.10+, switch to `_ToSMetadata | None`
    remote: Optional[RemoteToSMetadata] = None  # noqa: UP045

    def __lt__(self: Self, other: _MetadataPathPair) -> bool:
        """Compare the metadata version.

        Critical for sorting a list of metadata path pairs.
        """
        if not isinstance(other, _MetadataPathPair):
            return NotImplemented
        return self.metadata.version < other.metadata.version

    @property
    def latest_text(self: Self) -> str:
        """Get the latest text of the Terms of Service."""
        return (self.remote or self.metadata).text


class RemotePair(_MetadataPathPair):
    """Tuple of remote metadata and no path."""

    metadata: RemoteToSMetadata
    path: None = None
    remote: None = None


class LocalPair(_MetadataPathPair):
    """Tuple of local metadata and path."""

    metadata: LocalToSMetadata
    path: Path
