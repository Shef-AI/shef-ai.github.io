"""
Minimal (just what conda-index uses) filesystem abstraction.

Allows `fsspec <https://filesystem-spec.readthedocs.io/>`_ to be used to index
remote repositories, without making it a required dependency.
"""

from __future__ import annotations

import os
import os.path
import typing
from dataclasses import dataclass
from pathlib import Path

if typing.TYPE_CHECKING:  # pragma: no cover
    from fsspec import AbstractFileSystem


# Note fsspec uses / as a path separator on all platforms


@dataclass
class FileInfo:
    """
    Filename and a bit of stat information.
    """

    fn: str
    st_mtime: float | int
    st_size: int


class MinimalFS:
    """
    Filesystem API as needed by conda-index, for fsspec compatibility.
    """

    def open(self, path: str, mode: str = "rb"):
        return Path(path).open(mode)

    def stat(self, path: str):
        st_result = os.stat(path)
        return {
            "size": st_result.st_size,
            "mtime": st_result.st_mtime,
        }

    def join(self, *paths):
        return os.path.join(*paths)

    def listdir(self, path) -> typing.Iterable[dict]:
        for name in os.listdir(path):
            stat_result = os.stat(os.path.join(path, name))
            yield {
                "name": name,
                "mtime": stat_result.st_mtime,
                "size": stat_result.st_size,
            }

    def basename(self, path) -> str:
        return os.path.basename(path)


class FsspecFS(MinimalFS):
    """
    Wrap a fsspec filesystem to pass to :class:`ChannelIndex`
    """

    fsspec_fs: AbstractFileSystem

    def __init__(self, fsspec_fs):
        self.fsspec_fs = fsspec_fs

    def open(self, path: str, mode: str = "rb"):
        return self.fsspec_fs.open(path, mode)

    def stat(self, path: str):
        return self.fsspec_fs.stat(path)

    def join(self, *paths):
        # XXX
        return "/".join(p.rstrip("/") for p in paths)

    def listdir(self, path: str) -> list[dict]:
        return self.fsspec_fs.listdir(path, details=True)

    def basename(self, path: str) -> str:
        return path.rsplit("/", 1)[-1]
