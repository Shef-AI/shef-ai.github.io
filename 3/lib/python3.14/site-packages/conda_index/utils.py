import filecmp
import hashlib
from concurrent.futures.thread import ThreadPoolExecutor

from conda.base.constants import PLATFORM_DIRECTORIES as DEFAULT_SUBDIRS

from .utils_build import ensure_list as ensure_list
from .utils_build import get_lock as get_lock
from .utils_build import merge_or_update_dict as merge_or_update_dict
from .utils_build import move_with_fallback as move_with_fallback
from .utils_build import move_with_fallback_nolock as move_with_fallback_nolock
from .utils_build import try_acquire_locks as try_acquire_locks

DEFAULT_SUBDIRS = DEFAULT_SUBDIRS

CONDA_PACKAGE_EXTENSION_V1 = ".tar.bz2"
CONDA_PACKAGE_EXTENSION_V2 = ".conda"
CONDA_PACKAGE_EXTENSIONS = (
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSION_V1,
)

DEFAULT_SUBDIRS = set(DEFAULT_SUBDIRS)

__all__ = [
    "CONDA_PACKAGE_EXTENSIONS",
    "CONDA_PACKAGE_EXTENSION_V1",
    "CONDA_PACKAGE_EXTENSION_V2",
    "DEFAULT_SUBDIRS",
    "checksum",
    "checksums",
    "ensure_list",
    "file_contents_match",
    "get_lock",
    "human_bytes",
    "merge_or_update_dict",
    "move_with_fallback",
    "try_acquire_locks",
]
CONDA_PACKAGE_EXTENSION_V2 = ".conda"
CONDA_PACKAGE_EXTENSION_V1 = ".tar.bz2"
CONDA_PACKAGE_EXTENSIONS = (CONDA_PACKAGE_EXTENSION_V2, CONDA_PACKAGE_EXTENSION_V1)

# multithreaded checksums


def _checksum(fd, algorithm, buffersize=65536):
    hash_impl = getattr(hashlib, algorithm)()
    for block in iter(lambda: fd.read(buffersize), b""):
        hash_impl.update(block)
    return hash_impl.hexdigest()


def checksum(fn, algorithm, buffersize=1 << 18):
    """
    Calculate a checksum for a filename (not an open file).
    """
    with open(fn, "rb") as fd:
        return _checksum(fd, algorithm, buffersize)


def checksums(fn, algorithms, buffersize=1 << 18):
    """
    Calculate multiple checksums for a filename in parallel.
    """
    with ThreadPoolExecutor(max_workers=len(algorithms)) as e:
        # take care not to share hash_impl between threads
        results = [
            e.submit(checksum, fn, algorithm, buffersize) for algorithm in algorithms
        ]
    return [result.result() for result in results]


def file_contents_match(pathA, pathB):
    """
    Return True if pathA and pathB have identical contents.
    """

    return filecmp.cmp(pathA, pathB, shallow=False)


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.

    Examples:
        >>> human_bytes(42)
        '42 B'
        >>> human_bytes(1042)
        '1 KB'
        >>> human_bytes(10004242)
        '9.5 MB'
        >>> human_bytes(100000004242)
        '93.13 GB'
    """
    if n < 1024:
        return "%d B" % n
    k = n / 1024
    if k < 1024:
        return "%d KB" % round(k)
    m = k / 1024
    if m < 1024:
        return f"{m:.1f} MB"
    g = m / 1024
    return f"{g:.2f} GB"
