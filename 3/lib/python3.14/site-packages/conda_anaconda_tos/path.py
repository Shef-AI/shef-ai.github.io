# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Low-level path helpers."""

from __future__ import annotations

import hashlib
import os
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from conda.common.compat import on_win
from conda.common.configuration import custom_expandvars
from conda.models.channel import Channel
from platformdirs import user_cache_dir

from . import APP_NAME

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import datetime
    from typing import Final

#: Site metadata directory. This is the highest priority location.
SITE_TOS_ROOT: Final = "C:/ProgramData/conda/tos" if on_win else "/etc/conda/tos"

#: System metadata directory. Located in the conda installation.
SYSTEM_TOS_ROOT: Final = "$CONDA_ROOT/conda-meta/tos"

#: User metadata directory. Located in the user home directory.
USER_TOS_ROOT: Final = "~/.conda/tos"

#: Environment metadata directory. Located in the current conda environment.
ENV_TOS_ROOT: Final = "$CONDA_PREFIX/conda-meta/tos"

#: Search path for metadata directories.
SEARCH_PATH: Final = tuple(
    filter(
        None,
        (
            SITE_TOS_ROOT,
            "/var/lib/conda/tos" if not on_win else None,
            SYSTEM_TOS_ROOT,
            "$XDG_CONFIG_HOME/conda/tos",
            "~/.config/conda/tos",
            USER_TOS_ROOT,
            ENV_TOS_ROOT,
            # mirrors $CONDARC
            "$CONDATOS",
        ),
    ),
)

#: Metadata file glob pattern.
TOS_GLOB: Final = "*.json"

#: OS and user specific metadata cache directory.
CACHE_DIR: Final = Path(user_cache_dir(APP_NAME, appauthor=APP_NAME))


@cache
def hash_channel(channel: str | Channel) -> str:
    """Hash the channel to remove problematic characters (e.g. /)."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError(
            "`channel` must have a base URL. "
            "(hint: `conda.models.channel.MultiChannel` cannot be hashed)"
        )

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def get_path(path: str | os.PathLike[str] | Path) -> Path:
    """Expand environment variables and user home in the path."""
    if isinstance(path, str):
        path = custom_expandvars(path, os.environ)
    elif not isinstance(path, Path):
        raise TypeError("`path` must be a string or `pathlib.Path`.")
    return Path(path).expanduser()


def get_search_path(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all root metadata paths ordered from highest to lowest priority."""
    seen: set[Path] = set()
    for tos_root in (*SEARCH_PATH, *(extend_search_path or ())):
        if (path := get_path(tos_root)).is_dir() and path not in seen:
            yield path
            seen.add(path)


def get_tos_dir(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
) -> Path:
    """Get the metadata directory for the given channel."""
    return get_path(tos_root) / hash_channel(channel)


def get_metadata_path(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
    version: datetime,
) -> Path:
    """Get the metadata file path for the given channel and version."""
    return get_tos_dir(tos_root, channel) / f"{version.timestamp()}.json"


def get_all_channel_paths(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local metadata file paths."""
    for path in get_search_path(extend_search_path):
        yield from sorted(get_path(path).glob(f"*/{TOS_GLOB}"))


def get_channel_paths(
    channel: str | Channel,
    *,
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local metadata file paths for the given channel."""
    for path in get_search_path(extend_search_path):
        yield from sorted(get_tos_dir(path, channel).glob(TOS_GLOB))


def get_cache_path(channel: str | Channel) -> Path:
    """Get the metadata cache file path for the given channel."""
    return CACHE_DIR / f"{hash_channel(channel)}.cache"


def get_cache_paths() -> Iterator[Path]:
    """Get all local metadata cache file paths."""
    yield from sorted(CACHE_DIR.glob("*.cache"))
