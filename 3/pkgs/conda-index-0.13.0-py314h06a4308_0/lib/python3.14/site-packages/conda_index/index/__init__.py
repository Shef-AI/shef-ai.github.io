# Copyright (C) 2018-2022 Anaconda, Inc

from __future__ import annotations

import bz2
import functools
import hashlib
import json
import logging
import multiprocessing
import os
import sys
import time
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
from os.path import basename, getmtime, getsize, isfile, join
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import msgpack

if sys.version_info >= (3, 14):  # pragma: no cover
    import compression.zstd as zstd
else:
    import backports.zstd as zstd
from conda.models.version import VersionOrder  # sole remaining conda dependency here?
from conda_package_streaming import package_streaming
from jinja2 import Environment, PackageLoader

from .. import utils
from ..utils import (
    CONDA_PACKAGE_EXTENSION_V1,
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSIONS,
)
from . import rss, sqlitecache
from .fs import FileInfo

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, NotRequired, TypedDict

    from .cache import BaseCondaIndexCache, IndexedPackages, IndexedShard
    from .fs import MinimalFS

    V3Section = TypedDict(
        "V3Section",
        {
            "tar.bz2": dict[str, dict[str, Any]],
            "conda": dict[str, dict[str, Any]],
            "whl": dict[str, dict[str, Any]],
        },
        closed=True,
    )

    # in this style because "packages.conda" is not a Python identifier
    ShardDict = TypedDict(
        "ShardDict",
        {
            "packages": dict[str, dict[str, Any]],
            "packages.conda": dict[str, dict[str, Any]],
            "v3": NotRequired[V3Section],
        },
    )


log = logging.getLogger(__name__)

# zstd -T0 -b15 -e17 repodata.json
# level 16 gives a nice jump in ratio and decompress speed
# 15#repodata.json     : 229527083 ->  27834591 (x8.246),  112.3 MB/s, 2726.7 MB/s
# 16#repodata.json     : 229527083 ->  24457586 (x9.385),   47.6 MB/s, 3797.3 MB/s
# 17#repodata.json     : 229527083 ->  23358438 (x9.826),   30.2 MB/s, 3977.2 MB/s
ZSTD_COMPRESS_LEVEL = 16
# According to https://easyperf.net/blog/2024/05/10/Thread-Count-Scaling-Part3,
# 5 threads is the maximum useful number. Use cpu_count() // 2 in case of
# hyperthreading. A value of 0 disables multithreading
ZSTD_COMPRESS_THREADS = min((os.cpu_count() or 1) // 2, 5)


def logging_config():
    """Called by package extraction subprocesses to re-configure logging."""
    from . import logutil

    logutil.configure()


# use this for debugging, because ProcessPoolExecutor isn't pdb/ipdb friendly
class DummyExecutor(Executor):
    def map(self, func, *iterables):
        for iterable in iterables:
            for thing in iterable:
                yield func(thing)

    def submit(self, func, *args, **kwargs):
        class future:
            def result(self):
                return func(*args, **kwargs)

        return future()


local_index_timestamp = 0
cached_index = None
local_subdir = ""
local_output_folder = ""
cached_channels = []
channel_data = {}

# os.cpu_count() "Return the number of CPUs in the system. Returns None if
# undetermined."
MAX_THREADS_DEFAULT = os.cpu_count() or 1
if (
    sys.platform == "win32"
):  # see https://github.com/python/cpython/commit/8ea0fd85bc67438f679491fae29dfe0a3961900a
    MAX_THREADS_DEFAULT = min(48, MAX_THREADS_DEFAULT)  # pragma: no cover
LOCK_TIMEOUT_SECS = 3 * 3600
LOCKFILE_NAME = ".lock"


def _ensure_valid_channel(local_folder, subdir):
    for folder in {subdir, "noarch"}:
        path = os.path.join(local_folder, folder)
        if not os.path.isdir(path):
            os.makedirs(path)


def update_index(
    dir_path,
    output_dir=None,
    check_md5=False,
    channel_name=None,
    patch_generator=None,
    threads: int | None = MAX_THREADS_DEFAULT,
    verbose=False,
    progress=False,
    subdirs=None,
    warn=True,
    current_index_versions=None,
    debug=False,
    write_bz2=True,
    write_zst=False,
    write_run_exports=False,
    html_dependencies=False,
    repodata_v3=False,
):
    """
    High-level interface to ``ChannelIndex``. Index all subdirs under
    ``dir_path``. Output to `output_dir`, or under the input directory if
    `output_dir` is not given. Writes updated ``channeldata.json``.

    The input ``dir_path`` should at least contain a directory named ``noarch``.
    The path tree therein is treated as a full channel, with a level of subdirs,
    each subdir having an update to repodata.json. The full channel will also
    have a channeldata.json file.
    """
    _, dirname = os.path.split(dir_path)
    if dirname in utils.DEFAULT_SUBDIRS:
        if warn:
            log.warning(
                "The update_index function has changed to index all subdirs at once.  You're pointing it at a single subdir.  "
                "Please update your code to point it at the channel root, rather than a subdir. "
                "Use -s=<subdir> to update a single subdir."
            )
        raise ValueError(
            "Does not accept a single subdir, or a path named "
            "like one of the standard subdirs."
        )

    channel_index = ChannelIndex(
        dir_path,
        channel_name,
        subdirs=subdirs,
        threads=threads,
        deep_integrity_check=check_md5,
        debug=debug,
        output_root=output_dir,
        write_bz2=write_bz2,
        write_zst=write_zst,
        write_run_exports=write_run_exports,
        html_dependencies=html_dependencies,
        repodata_v3=repodata_v3,
    )

    channel_index.index(
        patch_generator=patch_generator,
        verbose=verbose,
        progress=progress,
        current_index_versions=current_index_versions,
    )

    channel_index.update_channeldata()


def _make_seconds(timestamp):
    timestamp = int(timestamp)
    if timestamp > 253402300799:  # 9999-12-31
        timestamp //= (
            1000  # convert milliseconds to seconds; see conda/conda-build#1988
        )
    return timestamp


# ==========================================================================


REPODATA_VERSION = 1
REPODATA_SHARDS_VERSION = (
    1  # defined in CEP-16 to be 1; not written by prefix.dev tools
)
CHANNELDATA_VERSION = 1
RUN_EXPORTS_VERSION = 1
REPODATA_REVISION_V3 = "v3"
REPODATA_JSON_FN = "repodata.json"
REPODATA_FROM_PKGS_JSON_FN = "repodata_from_packages.json"
REPODATA_SHARDS_FN = "repodata_shards.msgpack.zst"
REPODATA_SHARDS_FROM_PKGS_FN = "repodata_shards_from_packages.msgpack.zst"
RUN_EXPORTS_JSON_FN = "run_exports.json"
CHANNELDATA_FIELDS = (
    "description",
    "dev_url",
    "doc_url",
    "doc_source_url",
    "home",
    "license",
    "reference_package",
    "source_url",
    "source_git_url",
    "source_git_tag",
    "source_git_rev",
    "summary",
    "version",
    "subdirs",
    "icon_url",
    "icon_hash",  # "md5:abc123:12"
    "run_exports",
    "binary_prefix",
    "text_prefix",
    "activate.d",
    "deactivate.d",
    "pre_link",
    "post_link",
    "pre_unlink",
    "tags",
    "identifiers",
    "keywords",
    "recipe_origin",
    "commits",
)


def _apply_instructions(subdir, repodata, instructions, new_pkg_fixes=None):
    repodata.setdefault("removed", [])
    # apply to .tar.bz2 packages
    utils.merge_or_update_dict(
        repodata.get("packages", {}),
        instructions.get("packages", {}),
        merge=False,
        add_missing_keys=False,
    )

    if new_pkg_fixes is None:
        # we could have totally separate instructions for .conda than .tar.bz2, but it's easier if we assume
        #    that a similarly-named .tar.bz2 file is the same content as .conda, and shares fixes
        new_pkg_fixes = {
            k.replace(CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2): v
            for k, v in instructions.get("packages", {}).items()
        }

    # apply .tar.bz2 fixes to packages.conda
    utils.merge_or_update_dict(
        repodata.get("packages.conda", {}),
        new_pkg_fixes,
        merge=False,
        add_missing_keys=False,
    )
    # apply .conda-only fixes to packages.conda
    utils.merge_or_update_dict(
        repodata.get("packages.conda", {}),
        instructions.get("packages.conda", {}),
        merge=False,
        add_missing_keys=False,
    )

    for fn in instructions.get("revoke", ()):
        for key in ("packages", "packages.conda"):
            if key == "packages.conda" and fn.endswith(CONDA_PACKAGE_EXTENSION_V1):
                fn = fn.replace(CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2)
            records = repodata.get(key, {})
            if fn in records:
                records[fn]["revoked"] = True
                records[fn]["depends"].append("package_has_been_revoked")

    for fn in instructions.get("remove", ()):
        for key in ("packages", "packages.conda"):
            if key == "packages.conda" and fn.endswith(CONDA_PACKAGE_EXTENSION_V1):
                fn = fn.replace(CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2)
            records = repodata.get(key, {})
            popped = records.pop(fn, None)
            if popped:
                repodata["removed"].append(fn)
    repodata["removed"].sort()

    return repodata


def _get_jinja2_environment():
    def _filter_strftime(dt, dt_format):
        if isinstance(dt, (int, float)):
            if dt > 253402300799:  # 9999-12-31
                dt //= 1000  # convert milliseconds to seconds; see #1988
            dt = datetime.fromtimestamp(dt, tz=timezone.utc)
        return dt.strftime(dt_format)

    def _filter_add_href(text, link, **kwargs):
        if link:
            kwargs_list = [f'href="{link}"']
            kwargs_list += [f'{k}="{v}"' for k, v in kwargs.items()]
            return "<a {}>{}</a>".format(" ".join(kwargs_list), text)
        else:
            return text

    def _filter_to_title(obj):
        depends_str = "\n".join(obj.get("depends", []))
        return (
            # name v0.0.0 pyABC_X
            f"{obj.get('name')} v{obj.get('version')} {obj.get('build')}"
            "\n\n"
            "depends:\n"
            # each dependency on a new line
            f"{depends_str}"
        )

    environment = Environment(
        loader=PackageLoader("conda_index", "templates"),
    )
    environment.filters["human_bytes"] = utils.human_bytes
    environment.filters["strftime"] = _filter_strftime
    environment.filters["add_href"] = _filter_add_href
    environment.filters["to_title"] = _filter_to_title
    environment.trim_blocks = True
    environment.lstrip_blocks = True

    return environment


def _make_subdir_index_html(
    channel_name, subdir, repodata_packages, extra_paths, html_dependencies
):
    environment = _get_jinja2_environment()
    template = environment.get_template("subdir-index.html.j2")
    rendered_html = template.render(
        title="{}/{}".format(channel_name or "", subdir),
        packages=repodata_packages,
        current_time=datetime.now(timezone.utc),
        extra_paths=extra_paths,
        html_dependencies=html_dependencies,
    )
    return rendered_html


def _make_channeldata_index_html(channel_name, channeldata):
    environment = _get_jinja2_environment()
    template = environment.get_template("channeldata-index.html.j2")
    rendered_html = template.render(
        title=channel_name,
        packages=channeldata["packages"],
        subdirs=channeldata["subdirs"],
        current_time=datetime.now(timezone.utc),
    )
    return rendered_html


def thread_executor_factory(debug, threads):
    return (
        DummyExecutor()
        if (debug or threads == 1)
        else ProcessPoolExecutor(
            threads,
            initializer=logging_config,
            mp_context=multiprocessing.get_context("spawn"),
        )
    )  # "fork" start method may cause hangs even on Linux?


class ChannelIndex:
    """
    Class implementing ``update_index``. Allows for more fine-grained control of
    output.

    See the implementation of ``conda_index.cli`` for usage.

    :param channel_root: Path to channel, or just the channel cache if channel_url is provided.
    :param channel_name: Name of channel; defaults to last path segment of channel_root.
    :param subdirs: subdirs to index.
    :param output_root: Path to write repodata.json etc; defaults to channel_root.
    :param channel_url: fsspec URL where package files live. If provided, channel_root will only be used for cache and index output.
    :param fs: ``MinimalFS`` instance to be used with channel_url. Wrap fsspec AbstractFileSystem with ``conda_index.index.fs.FsspecFS(fs)``.
    :param base_url: Add ``base_url/<subdir>`` to repodata.json to be able to host packages separate from repodata.json
    :param save_fs_state: Pass False to use cached filesystem state instead of ``os.listdir(subdir)``
    :param write_monolithic: Pass True to write large 'repodata.json' with all packages.
    :param write_shards: Pass True to write sharded repodata.msgpack and per-package fragments.
    :param html_dependencies: Pass True to include dependency popups in generated HTML index files.
    :param update_only: Pass True to only add or update, but not remove packages from the database.
    """

    fs: MinimalFS | None = None
    channel_url: str | None = None

    def __init__(
        self,
        channel_root: Path | str,
        channel_name: str | None,
        subdirs: Iterable[str] | None = None,
        threads: int | None = MAX_THREADS_DEFAULT,
        deep_integrity_check=False,
        debug=False,
        output_root=None,  # write repodata.json etc. to separate folder?
        cache_class: type[BaseCondaIndexCache] = sqlitecache.CondaIndexCache,
        write_bz2=False,
        write_zst=False,
        write_run_exports=False,
        compact_json=True,
        write_monolithic=True,
        write_shards=False,
        html_dependencies=False,
        *,
        channel_url: str | None = None,
        fs: MinimalFS | None = None,
        base_url: str | None = None,
        save_fs_state=True,
        write_current_repodata=True,
        upstream_stage: str = "fs",
        cache_kwargs=None,
        update_only=False,
        repodata_v3=False,
    ):
        if threads is None:
            threads = MAX_THREADS_DEFAULT

        if (fs or channel_url) and not (fs and channel_url):
            raise TypeError("Both or none of fs, channel_url must be provided.")

        self.fs = fs
        self.channel_url = channel_url

        self.channel_root = Path(channel_root)
        self.cache_class = cache_class
        self.output_root = Path(output_root) if output_root else self.channel_root
        self.channel_name = channel_name or basename(str(channel_root).rstrip("/"))
        self._subdirs = subdirs
        # no lambdas in pickleable
        self.thread_executor_factory = functools.partial(
            thread_executor_factory, debug, threads
        )
        self.debug = debug
        self.deep_integrity_check = deep_integrity_check
        self.write_bz2 = write_bz2
        self.write_zst = write_zst
        self.write_run_exports = write_run_exports
        self.write_monolithic = write_monolithic
        self.write_shards = write_shards
        self.html_dependencies = html_dependencies
        self.compact_json = compact_json
        self.base_url = base_url
        self.save_fs_state = save_fs_state
        self.write_current_repodata = write_current_repodata
        self.upstream_stage = upstream_stage
        self.update_only = update_only
        self.repodata_v3 = repodata_v3

        self.cache_kwargs = cache_kwargs

        # Timestamp for this indexing run (consistent across all subdirs)
        now_dt = datetime.now(tz=timezone.utc)
        self.created_at = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def cache_for_subdir(self, subdir):
        cache = self.cache_class(
            channel_root=self.channel_root,
            subdir=subdir,
            fs=self.fs,
            channel_url=self.channel_url,
            upstream_stage=self.upstream_stage,
            update_only=self.update_only,
            **self.cache_kwargs or {},
        )  # type: ignore
        if cache.cache_is_brand_new:
            # guaranteed to be only thread doing this?
            cache.convert()
        return cache

    def index(
        self,
        patch_generator,
        verbose=False,
        progress=False,
        current_index_versions=None,
    ):
        """
        Examine all changed packages under ``self.channel_root``, updating
        ``index.html`` for each subdir.
        """
        if verbose:
            log.debug(
                "ChannelIndex.index(verbose=...) is a no-op. Alter log levels for %s to control verbosity.",
                __name__,
            )

        subdirs = self.detect_subdirs()

        # begin non-stop "extract packages into cache";
        # extract_subdir_to_cache manages subprocesses. Keeps cores busy
        # during write/patch/update channeldata steps.
        def extract_subdirs_to_cache():  # is the 'prepare' step in 'index_prepared_subdir'
            executor = ThreadPoolExecutor(max_workers=1)

            def extract_args():
                for subdir in subdirs:
                    # .cache is currently in channel_root not output_root
                    _ensure_valid_channel(self.channel_root, subdir)
                    subdir_path = join(self.channel_root, subdir)
                    yield (subdir, verbose, progress, subdir_path)

            def extract_wrapper(args: tuple):
                # runs in thread
                subdir, verbose, progress, subdir_path = args
                with self.cache_for_subdir(subdir) as cache:
                    # exactly these packages (unless they are un-indexable) will
                    # be in the output repodata
                    if self.save_fs_state:
                        cache.save_fs_state(subdir_path)
                    return self.extract_subdir_to_cache(
                        subdir, verbose, progress, subdir_path, cache
                    )

            # map() gives results in order passed, not in order of
            # completion. If using multiple threads, switch to
            # submit() / as_completed().
            return executor.map(extract_wrapper, extract_args())

        # Collect repodata from packages, save to
        # REPODATA_FROM_PKGS_JSON_FN file
        with self.thread_executor_factory() as index_process:
            futures = []
            for subdir in extract_subdirs_to_cache():
                for indexer, condition in (
                    (self.index_patch_subdir, self.write_monolithic),
                    (self.index_patch_subdir_shards, self.write_shards),
                ):
                    if condition:
                        futures.append(
                            index_process.submit(
                                functools.partial(
                                    indexer,
                                    subdir=subdir,
                                    verbose=verbose,
                                    progress=progress,
                                    patch_generator=patch_generator,
                                    current_index_versions=current_index_versions,
                                )
                            )
                        )
            # limited API to support DummyExecutor
            for future in futures:
                result = future.result()
                log.info(f"Completed {result}")

    # old name
    def index_prepared_subdir(
        self,
        subdir: str,
        verbose: bool,
        progress: bool,
        patch_generator,
        current_index_versions,
    ):  # pragma: no cover
        return self.index_patch_subdir(
            subdir, verbose, progress, patch_generator, current_index_versions
        )

    def index_patch_subdir(
        self,
        subdir: str,
        verbose: bool,
        progress: bool,
        patch_generator,
        current_index_versions,
    ):
        """
        Create repodata_from_packages.json by calling index_subdir, then patch.
        """
        log.info("Subdir: %s Gathering repodata", subdir)

        repodata_from_packages = self.index_subdir(
            subdir, verbose=verbose, progress=progress
        )

        log.info("%s Writing pre-patch repodata", subdir)
        self._write_repodata(
            subdir,
            repodata_from_packages,
            REPODATA_FROM_PKGS_JSON_FN,
        )

        # Apply patch instructions.
        log.info("%s Applying patch instructions", subdir)
        patched_repodata, _ = self._patch_repodata(
            subdir, repodata_from_packages, patch_generator
        )

        # Save patched and augmented repodata. If the contents
        # of repodata have changed, write a new repodata.json.
        # Create associated index.html.

        log.info("%s Writing patched repodata", subdir)

        self._write_repodata(subdir, patched_repodata, REPODATA_JSON_FN)

        if self.write_current_repodata:
            log.info("%s Building current_repodata subset", subdir)
            self._write_repodata(
                subdir,
                self._build_current_repodata(
                    subdir, patched_repodata, current_index_versions
                ),
                json_filename="current_repodata.json",
            )
        else:
            self._remove_repodata(subdir, "current_repodata.json")

        if self.write_run_exports:
            log.info("%s Building run_exports data", subdir)
            run_exports_data = self.build_run_exports_data(subdir)

            log.info("%s Writing run_exports.json", subdir)
            self._write_repodata(
                subdir,
                run_exports_data,
                json_filename=RUN_EXPORTS_JSON_FN,
            )

        log.info("%s Writing index HTML", subdir)

        self._write_subdir_index_html(subdir, patched_repodata)

        log.debug("%s finish", subdir)

        return subdir

    def _build_current_repodata(self, subdir, patched_repodata, current_index_versions):
        """
        Isolate call to build_current_repodata(), skipping import if not used.
        """
        from .current_repodata import build_current_repodata

        current_repodata = build_current_repodata(
            subdir, patched_repodata, pins=current_index_versions
        )
        return current_repodata

    def index_patch_subdir_shards(
        self,
        subdir: str,
        verbose: bool,
        progress: bool,
        patch_generator,
        current_index_versions=None,  # unused
    ):
        """
        Create repodata_from_packages, then patch.
        """
        log.info("Subdir: %s Gathering repodata", subdir)

        shards_from_packages = self.index_subdir_shards(
            subdir, verbose=verbose, progress=progress
        )

        log.info("%s Writing pre-patch shards", subdir)

        patched_path = self.channel_root / subdir / REPODATA_SHARDS_FROM_PKGS_FN
        self._maybe_write(
            patched_path,
            zstd.compress(sqlitecache.packb_typed(shards_from_packages)),
        )  # type: ignore

        # Apply patch instructions.
        log.info("%s Applying patch instructions", subdir)
        patched_packages, _ = self._patch_repodata_shards(
            subdir, shards_from_packages, patch_generator
        )

        # Save patched and augmented repodata. If the contents
        # of repodata have changed, write a new repodata.json.
        # Create associated index.html.

        log.info("%s Writing patched repodata", subdir)

        repodata_shards = shards_from_packages.copy()
        repodata_shards["shards"] = {}

        for pkg, record in patched_packages.items():
            shard_data = zstd.compress(sqlitecache.packb_typed(record))
            shard_hash = hashlib.sha256(shard_data).digest()
            repodata_shards["shards"][pkg] = shard_hash
            output_path = self.output_root / subdir / f"{shard_hash.hex()}.msgpack.zst"
            if not output_path.exists():
                output_path.write_bytes(shard_data)

        patched_path = self.channel_root / subdir / REPODATA_SHARDS_FN
        self._maybe_write(
            patched_path,
            zstd.compress(sqlitecache.packb_typed(repodata_shards)),
        )  # type: ignore

        log.debug("%s finish", subdir)

        return subdir

    def index_subdir_shards(self, subdir, verbose=False, progress=False):
        """
        Generate sharded repodata from the cache.

        Must call `extract_subdir_to_cache()` first or will be outdated.
        """

        with self.cache_for_subdir(subdir) as cache:  # type: ignore
            log.debug("Building repodata for %s/%s", self.channel_name, subdir)

            shards = {}

            created_at = self.created_at

            shards_index = {
                "version": REPODATA_SHARDS_VERSION,
                "info": {
                    "base_url": "",  # pixi requires this key
                    "shards_base_url": "",  # and this one
                    "created_at": created_at,
                    "subdir": subdir,
                },
                "shards": shards,
            }

            if self.base_url:
                # per https://github.com/conda-incubator/ceps/blob/main/cep-15.md
                shards_index["info"]["base_url"] = (
                    f"{self.base_url.rstrip('/')}/{subdir}/"
                )

            (self.output_root / subdir).mkdir(parents=True, exist_ok=True)

            v3_data: V3Section = {
                "tar.bz2": {},
                "conda": {},
                "whl": {},
            }

            for shard in cache.indexed_shards():
                repodata_shard = self._indexed_shard_to_repodata(shard)
                # Higher compression levels are a waste of time for tiny gains on this
                # collection of small objects.
                shard_bytes = zstd.compress(sqlitecache.packb_typed(repodata_shard))
                shard_hash = hashlib.sha256(shard_bytes).digest()
                output_path = (
                    self.output_root / subdir / f"{shard_hash.hex()}.msgpack.zst"
                )
                if not output_path.exists():
                    output_path.write_bytes(shard_bytes)
                shards[shard.name] = shard_hash

                if self.repodata_v3:
                    for section, records in repodata_shard.get("v3", {}).items():
                        v3_data[section].update(records)

            if self.repodata_v3:
                revision_data = self._make_repodata_revision_data(v3_data)
                revision = revision_data.pop("revision")
                shards_index["info"]["repodata_revisions"] = {revision: revision_data}

            return shards_index

    def index_subdir(self, subdir, verbose=False, progress=False):
        """
        Generate repodata from the cache.

        Must call `extract_subdir_to_cache()` first or will be outdated.
        """

        with self.cache_for_subdir(subdir) as cache:
            log.debug("Building repodata for %s/%s", self.channel_name, subdir)

            indexed_packages = cache.indexed_packages()

        new_repodata = {
            "packages": indexed_packages.packages,
            "packages.conda": indexed_packages.packages_conda,
            "info": {
                "subdir": subdir,
            },
            "repodata_version": REPODATA_VERSION,
            "removed": [],  # can be added by patch/hotfix process
        }

        if self.repodata_v3:
            v3_packages = self._extract_indexed_packages_v3(indexed_packages)
            new_repodata["v3"] = v3_packages
            new_repodata["packages"] = {}
            new_repodata["packages.conda"] = {}
            revision_data = self._make_repodata_revision_data(v3_packages)
            revision = revision_data.pop("revision")
            new_repodata["info"]["repodata_revisions"] = {revision: revision_data}

        if self.base_url:
            # per https://github.com/conda-incubator/ceps/blob/main/cep-15.md
            new_repodata["info"]["base_url"] = f"{self.base_url.rstrip('/')}/{subdir}/"
            new_repodata["repodata_version"] = 2

        return new_repodata

    @staticmethod
    def _v3_key_for_path(path: str) -> str | None:
        for extension in (".tar.bz2", ".conda", ".whl"):
            if path.endswith(extension):
                return path[: -len(extension)]
        return None

    def _extract_indexed_packages_v3(
        self, indexed_packages: IndexedPackages
    ) -> V3Section:
        """
        Return all packages from IndexedPackages as the "v3": {...} section.
        """
        v3: V3Section = {
            "tar.bz2": {},
            "conda": {},
            "whl": {},
        }
        for section, records in (
            ("tar.bz2", indexed_packages.packages),
            ("conda", indexed_packages.packages_conda),
            ("whl", indexed_packages.packages_whl),
        ):
            for filename, record in records.items():
                key = self._v3_key_for_path(filename)
                if key is None:
                    log.warning("%s has unsupported extension", filename)
                    continue

                # Per draft wheel-in-conda work, key is conda-like so that some
                # conda-like parsing can occur on the key only. So we derive the
                # key here. `record["fn"]` contains the filename or URL.
                if section == "whl":
                    name = record.get("name", None)
                    version = record.get("version", None)
                    build = record.get("build", None)
                    if name is None or version is None or build is None:
                        log.warning(
                            "%s: v3 whl records require name, version, and build; skipping",
                            filename,
                        )
                        continue
                    key = f"{name}-{version}-{build}"

                v3[section][key] = record

        return v3

    def _indexed_shard_to_repodata(self, indexed_shard: IndexedShard) -> ShardDict:
        if self.repodata_v3:
            shard_data: ShardDict = {
                "packages": {},
                "packages.conda": {},
                "v3": self._extract_indexed_packages_v3(indexed_shard),
            }
        else:
            shard_data = {
                "packages": indexed_shard.packages,
                "packages.conda": indexed_shard.packages_conda,
            }
        return shard_data

    @staticmethod
    def _make_repodata_revision_data(
        revision_data: V3Section,
    ) -> dict[str, int | str | None]:
        """
        Return { "revision": 3, ... } dict with package statistics derived from
        revision_data, which is similar to monolithic repodata.
        """
        timestamps = []
        n_packages = 0
        for section_records in revision_data.values():
            n_packages += len(section_records)
            for record in section_records.values():
                timestamp = record.get("timestamp")
                if isinstance(timestamp, (int, float)):
                    timestamps.append(int(timestamp))

        return {
            "revision": REPODATA_REVISION_V3,
            "n_packages": n_packages,
            "oldest": min(timestamps) if timestamps else None,
            "newest": max(timestamps) if timestamps else None,
        }

    def extract_subdir_to_cache(
        self,
        subdir: str,
        verbose,
        progress,
        subdir_path,
        cache: sqlitecache.CondaIndexCache,
    ) -> str:
        """
        Extract all changed packages into the subdir cache.

        Return name of subdir.
        """
        log.debug("%s find packages to extract", subdir)

        # list so tqdm can show progress
        extract = [
            FileInfo(
                fn=cache.plain_path(row["path"]),
                st_mtime=row["mtime"],
                st_size=row["size"],
            )
            for row in cache.changed_packages()
        ]

        log.debug("%s extract %d packages", subdir, len(extract))

        # now updates own stat cache
        extract_func = functools.partial(
            cache.extract_to_cache_info_object, self.channel_root, subdir
        )

        start_time = time.time()
        size_processed = 0

        with self.thread_executor_factory() as thread_executor:
            for fn, mtime, size, index_json in thread_executor.map(
                extract_func, extract
            ):
                # XXX allow size to be None or get from "bytes sent through
                # checksum algorithm" e.g. for fsspec where size may not be
                # known in advance
                size_processed += size  # even if processed incorrectly
                # fn can be None if the file was corrupt or no longer there
                if fn and mtime:
                    if index_json:
                        pass  # correctly indexed a package! index_subdir will fetch.
                    else:
                        log.error(
                            "Package at %s did not contain valid index.json data.  Please"
                            " check the file and remove/redownload if necessary to obtain "
                            "a valid package.",
                            os.path.join(subdir_path, fn),
                        )
            end_time = time.time()
            try:
                bytes_sec = size_processed / (end_time - start_time)
            except ZeroDivisionError:  # pragma: no cover
                bytes_sec = 0
        log.info(
            "%s cached %s from %s packages at %s/second",
            subdir,
            utils.human_bytes(size_processed),
            len(extract),
            utils.human_bytes(bytes_sec),
        )

        return subdir

    # region: channeldata

    def channeldata_path(self):
        channeldata_file = os.path.join(self.output_root, "channeldata.json")
        return channeldata_file

    def update_channeldata(self, rss=False):
        """
        Update channeldata based on re-reading output `repodata.json` and existing
        `channeldata.json`. Call after index() if channeldata is needed.
        """
        subdirs = self.detect_subdirs()

        # Skip locking; only writes the channeldata.

        # Keep channeldata in memory, update with each subdir.
        channel_data = {}
        channeldata_file = self.channeldata_path()
        if os.path.isfile(channeldata_file):
            with open(channeldata_file) as f:
                channel_data = json.load(f)

        for subdir in subdirs:
            log.info("Channeldata subdir: %s", subdir)
            log.debug("%s read repodata", subdir)
            with open(
                os.path.join(self.output_root, subdir, REPODATA_JSON_FN)
            ) as repodata:
                patched_repodata = json.load(repodata)

            self._update_channeldata(channel_data, patched_repodata, subdir)

            log.debug("%s channeldata finished", subdir)

        # Create and write the rss feed.
        if rss:
            self._write_rss(channel_data)

        # Create and write channeldata.
        self._write_channeldata_index_html(channel_data)
        log.debug("write channeldata")
        self._write_channeldata(channel_data)

    # endregion

    def detect_subdirs(self):
        if not self._subdirs:
            detected_subdirs = {
                subdir.name
                for subdir in os.scandir(self.channel_root)
                if subdir.name in utils.DEFAULT_SUBDIRS and subdir.is_dir()
            }
            log.debug("found subdirs %s", detected_subdirs)
            self.subdirs = sorted(detected_subdirs | {"noarch"})
        else:
            self.subdirs = sorted(set(self._subdirs))
            if "noarch" not in self.subdirs:
                log.warning("Indexing %s does not include 'noarch'", self.subdirs)
        return self.subdirs

    def _write_repodata(self, subdir, repodata, json_filename):
        """
        Write repodata to :json_filename, but only if changed.
        """
        repodata_json_path = join(self.channel_root, subdir, json_filename)
        new_repodata = self.json_dumps(repodata)
        write_result = self._maybe_write(
            repodata_json_path, new_repodata, write_newline_end=False
        )
        # write repodata.json.bz2 if it doesn't exist, even if repodata.json has
        # not changed
        repodata_bz2_path = repodata_json_path + ".bz2"
        repodata_zst_path = repodata_json_path + ".zst"
        if write_result or not os.path.exists(repodata_bz2_path):
            if self.write_bz2:
                bz2_content = bz2.compress(new_repodata.encode("utf-8"))
                self._maybe_write(repodata_bz2_path, bz2_content)
            else:
                self._maybe_remove(repodata_bz2_path)
            if self.write_zst:
                repodata_zst_content = zstd.compress(
                    new_repodata.encode("utf-8"),
                    options={
                        zstd.CompressionParameter.compression_level: ZSTD_COMPRESS_LEVEL,
                        zstd.CompressionParameter.nb_workers: ZSTD_COMPRESS_THREADS,
                    },
                )
                self._maybe_write(repodata_zst_path, repodata_zst_content)
            else:
                self._maybe_remove(repodata_zst_path)
        return write_result

    def _remove_repodata(self, subdir, json_filename):
        """
        Remove json_filename and variants, to avoid keeping outdated repodata.
        """
        repodata_json_path = join(self.channel_root, subdir, json_filename)
        repodata_bz2_path = repodata_json_path + ".bz2"
        repodata_zst_path = repodata_json_path + ".zst"
        self._maybe_remove(repodata_json_path)
        self._maybe_remove(repodata_bz2_path)
        self._maybe_remove(repodata_zst_path)

    def _write_subdir_index_html(self, subdir, repodata):
        repodata_legacy_packages = repodata["packages"]
        repodata_conda_packages = repodata["packages.conda"]

        repodata_packages = {}
        repodata_packages.update(repodata_legacy_packages)
        repodata_packages.update(repodata_conda_packages)

        subdir_path = join(self.channel_root, subdir)

        def _add_extra_path(extra_paths, path):
            if isfile(join(self.channel_root, path)):
                md5sum, sha256sum = utils.checksums(path, ("md5", "sha256"))
                extra_paths[basename(path)] = {
                    "size": getsize(path),
                    "timestamp": int(getmtime(path)),
                    "sha256": sha256sum,
                    "md5": md5sum,
                }

        extra_paths = {}
        _add_extra_path(extra_paths, join(subdir_path, REPODATA_JSON_FN))
        if self.write_bz2:
            _add_extra_path(extra_paths, join(subdir_path, REPODATA_JSON_FN + ".bz2"))
        _add_extra_path(extra_paths, join(subdir_path, REPODATA_FROM_PKGS_JSON_FN))
        if self.write_bz2:
            _add_extra_path(
                extra_paths, join(subdir_path, REPODATA_FROM_PKGS_JSON_FN + ".bz2")
            )

        _add_extra_path(extra_paths, join(subdir_path, "patch_instructions.json"))
        rendered_html = _make_subdir_index_html(
            self.channel_name,
            subdir,
            repodata_packages,
            extra_paths,
            self.html_dependencies,
        )
        assert rendered_html
        index_path = join(subdir_path, "index.html")
        return self._maybe_write(index_path, rendered_html)

    def _write_rss(self, channeldata):
        log.info("Build RSS")
        rss_text = rss.get_rss(self.channel_name, channeldata)
        rss_path = join(self.channel_root, "rss.xml")
        self._maybe_write(rss_path, rss_text)
        log.info("Built RSS")

    def _write_channeldata_index_html(self, channeldata):
        rendered_html = _make_channeldata_index_html(self.channel_name, channeldata)
        assert rendered_html
        index_path = join(self.channel_root, "index.html")
        self._maybe_write(index_path, rendered_html)

    def _update_channeldata(self, channel_data, repodata, subdir):
        legacy_packages = repodata["packages"]
        conda_packages = repodata["packages.conda"]

        use_these_legacy_keys = set(legacy_packages.keys()) - {
            k[:-6] + CONDA_PACKAGE_EXTENSION_V1 for k in conda_packages.keys()
        }
        all_repodata_packages = conda_packages.copy()
        all_repodata_packages.update(
            {k: legacy_packages[k] for k in use_these_legacy_keys}
        )
        package_data = channel_data.get("packages", {})

        # Pay special attention to groups that have run_exports - we
        # need to process each version group by version; take newest per
        # version group.  We handle groups that are not in the index at
        # all yet similarly, because we can't check if they have any
        # run_exports.

        # This is more deterministic than, but slower than the old "newest
        # timestamp across all versions if no run_exports", unsatisfying
        # when old versions get new builds. When channeldata.json is not
        # being built from scratch the speed difference is not noticable.

        def newest_by_name_and_version(all_repodata_packages):
            namever = {}

            for fn, package in all_repodata_packages.items():
                key = (package["name"], package["version"])
                timestamp = package.get("timestamp", 0)
                existing = namever.get(key)
                if not existing or existing[1].get("timestamp", 0) < timestamp:
                    namever[key] = (fn, package)

            return list(namever.values())

        groups = newest_by_name_and_version(all_repodata_packages)

        def _replace_if_newer_and_present(pd, data, existing_record, data_newer, k):
            if data.get(k) and (data_newer or not existing_record.get(k)):
                pd[k] = data[k]
            else:
                pd[k] = existing_record.get(k)

        # unzipping
        fns, fn_dicts = [], []
        if groups:
            fns, fn_dicts = zip(*groups)

        with self.cache_for_subdir(subdir) as cache:
            load_func = cache.load_all_from_cache
            with self.thread_executor_factory() as thread_executor:
                for fn_dict, data in zip(fn_dicts, thread_executor.map(load_func, fns)):
                    # not reached when older channeldata.json matches
                    if data:
                        data.update(fn_dict)
                        name = data["name"]
                        # existing record
                        existing_record = package_data.get(name, {})
                        data_v = data.get("version", "0")
                        erec_v = existing_record.get("version", "0")
                        # are timestamps already normalized to seconds?
                        data_newer = VersionOrder(data_v) > VersionOrder(erec_v) or (
                            data_v == erec_v
                            and _make_seconds(data.get("timestamp", 0))
                            > _make_seconds(existing_record.get("timestamp", 0))
                        )

                        package_data[name] = package_data.get(name, {})
                        # keep newer value for these
                        for k in (
                            "description",
                            "dev_url",
                            "doc_url",
                            "doc_source_url",
                            "home",
                            "license",
                            "source_url",
                            "source_git_url",
                            "summary",
                            "icon_url",
                            "icon_hash",
                            "tags",
                            "identifiers",
                            "keywords",
                            "recipe_origin",
                            "version",
                        ):
                            _replace_if_newer_and_present(
                                package_data[name],
                                data,
                                existing_record,
                                data_newer,
                                k,
                            )

                        # keep any true value for these, since we don't distinguish subdirs
                        for k in (
                            "binary_prefix",
                            "text_prefix",
                            "activate.d",
                            "deactivate.d",
                            "pre_link",
                            "post_link",
                            "pre_unlink",
                        ):
                            package_data[name][k] = any(
                                (data.get(k), existing_record.get(k))
                            )

                        package_data[name]["subdirs"] = sorted(
                            list(set(existing_record.get("subdirs", []) + [subdir]))
                        )
                        # keep one run_exports entry per version of the package, since these vary by version
                        run_exports = existing_record.get("run_exports", {})
                        exports_from_this_version = data.get("run_exports")
                        if exports_from_this_version:
                            run_exports[data_v] = data.get("run_exports")
                        package_data[name]["run_exports"] = run_exports
                        package_data[name]["timestamp"] = _make_seconds(
                            max(
                                data.get("timestamp", 0),
                                channel_data.get(name, {}).get("timestamp", 0),
                            )
                        )

        channel_data.update(
            {
                "channeldata_version": CHANNELDATA_VERSION,
                "subdirs": sorted(
                    list(set(channel_data.get("subdirs", []) + [subdir]))
                ),
                "packages": package_data,
            }
        )

    def json_dumps(self, data):
        """
        Format json based on class policy.
        """
        if self.compact_json:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        else:
            return json.dumps(data, sort_keys=True, indent=2) + "\n"

    def _write_channeldata(self, channeldata):
        # trim out commits, as they can take up a ton of space.  They're really only for the RSS feed.
        for pkg, pkg_dict in channeldata.get("packages", {}).items():
            channeldata["packages"][pkg] = {
                k: v for k, v in pkg_dict.items() if v is not None and k != "commits"
            }
        channeldata_path = join(self.channel_root, "channeldata.json")
        content = self.json_dumps(channeldata)
        self._maybe_write(channeldata_path, content, True)

    def build_run_exports_data(self, subdir, verbose=False, progress=False):
        """
        Return CEP-12 compliant run_exports metadata from the db cache.

        Must call `extract_subdir_to_cache()` first or will be outdated.
        """
        subdir_path = join(self.channel_root, subdir)

        log.debug("Building run_exports for %s", subdir_path)

        run_exports_packages = {}
        run_exports_conda_packages = {}

        with self.cache_for_subdir(subdir) as cache:
            for row in cache.run_exports():
                path, run_exports_data = row
                run_exports_data = {"run_exports": run_exports_data or {}}
                if path.endswith(CONDA_PACKAGE_EXTENSION_V1):
                    run_exports_packages[path] = run_exports_data
                elif path.endswith(CONDA_PACKAGE_EXTENSION_V2):
                    run_exports_conda_packages[path] = run_exports_data
                else:
                    log.warning("%s doesn't look like a conda package", path)

        new_run_exports_data = {
            "packages": run_exports_packages,
            "packages.conda": run_exports_conda_packages,
            "info": {
                "subdir": subdir,
                "version": RUN_EXPORTS_VERSION,
            },
        }

        return new_run_exports_data

    def _load_patch_instructions_tarball(self, subdir, patch_generator):
        instructions = {}

        target = "/".join((subdir, "patch_instructions.json"))
        for tar, member in package_streaming.stream_conda_component(
            patch_generator, component="pkg"
        ):
            if member.name == target:
                reader = tar.extractfile(member)
                assert reader, "tar member was not a regular file"
                instructions = json.load(reader)
        return instructions

    def _create_patch_instructions(self, subdir, repodata, patch_generator=None):
        gen_patch_path = patch_generator or join(self.channel_root, "gen_patch.py")
        if isfile(gen_patch_path):
            log.debug(f"using patch generator {gen_patch_path} for {subdir}")

            # https://stackoverflow.com/a/41595552/2127762
            from importlib.util import module_from_spec, spec_from_file_location

            spec = spec_from_file_location("a_b", gen_patch_path)
            if spec and spec.loader:
                mod = module_from_spec(spec)
                spec.loader.exec_module(mod)
            else:
                raise ImportError()

            instructions = mod._patch_repodata(repodata, subdir)

            if instructions.get("patch_instructions_version", 0) > 1:
                raise RuntimeError("Incompatible patch instructions version")

            return instructions
        else:
            if patch_generator:
                raise ValueError(
                    f"Specified metadata patch file '{patch_generator}' does not exist. "
                    "Please try an absolute path, or examine your relative path carefully "
                    "with respect to your cwd."
                )
            return {}

    def _write_patch_instructions(self, subdir, instructions):
        new_patch = self.json_dumps(instructions)
        patch_instructions_path = join(
            self.channel_root, subdir, "patch_instructions.json"
        )
        self._maybe_write(patch_instructions_path, new_patch, True)

    def _load_instructions(self, subdir):
        patch_instructions_path = join(
            self.channel_root, subdir, "patch_instructions.json"
        )
        if isfile(patch_instructions_path):
            log.debug("using patch instructions %s", patch_instructions_path)
            with open(patch_instructions_path) as fh:
                instructions = json.load(fh)
                if instructions.get("patch_instructions_version", 0) > 1:
                    raise RuntimeError("Incompatible patch instructions version")
                return instructions
        return {}

    def _write_or_load_instructions(self, subdir, instructions):
        if instructions:
            self._write_patch_instructions(subdir, instructions)
        else:
            instructions = self._load_instructions(subdir)
        if instructions.get("patch_instructions_version", 0) > 1:
            raise RuntimeError("Incompatible patch instructions version")
        return instructions

    def _patch_repodata(self, subdir, repodata, patch_generator: str | None = None):
        if patch_generator and patch_generator.endswith(CONDA_PACKAGE_EXTENSIONS):
            instructions = self._load_patch_instructions_tarball(
                subdir, patch_generator
            )
        else:
            instructions = self._create_patch_instructions(
                subdir, repodata, patch_generator
            )
        instructions = self._write_or_load_instructions(subdir, instructions)
        return _apply_instructions(subdir, repodata, instructions), instructions

    def _patch_repodata_shards(
        self, subdir, repodata_shards, patch_generator: str | None = None
    ):
        """
        Apply patches to sharded repodata.

        Return {"name":{shard data}}, not full repodata format.
        """
        # XXX see whether patch instructions are broken when applied per-shard

        instructions = {}

        if patch_generator and patch_generator.endswith(CONDA_PACKAGE_EXTENSIONS):
            instructions = self._load_patch_instructions_tarball(
                subdir, patch_generator
            )
        else:

            def per_shard_instructions():
                for pkg, reference in repodata_shards["shards"].items():
                    shard_path = (
                        self.output_root / subdir / f"{reference.hex()}.msgpack.zst"
                    )
                    shard = msgpack.loads(zstd.decompress(shard_path.read_bytes()))
                    yield (
                        pkg,
                        self._create_patch_instructions(subdir, shard, patch_generator),
                    )

            instructions = dict(per_shard_instructions())

        instructions = self._write_or_load_instructions(subdir, instructions)

        def per_shard_apply_instructions():
            # XXX refactor
            # otherwise _apply_instructions would repeat this work
            new_pkg_fixes = {
                k.replace(".tar.bz2", ".conda"): v
                for k, v in instructions.get("packages", {}).items()
            }

            for pkg, reference in repodata_shards["shards"].items():
                shard_path = (
                    self.output_root / subdir / f"{reference.hex()}.msgpack.zst"
                )
                shard = msgpack.loads(zstd.decompress(shard_path.read_bytes()))
                patched_shard = _apply_instructions(
                    subdir, shard, instructions, new_pkg_fixes=new_pkg_fixes
                )
                if "removed" in patched_shard and not patched_shard["removed"]:
                    del patched_shard["removed"]
                yield (pkg, patched_shard)

        return dict(per_shard_apply_instructions()), instructions

    def _maybe_write(self, path, content: str | bytes, write_newline_end=False):
        # Create the temp file next "path" so that we can use an atomic move, see
        # https://github.com/conda/conda-build/issues/3833
        temp_path = f"{path}.{uuid4()}"

        # intercept to support separate output_directory
        output_path = os.path.join(
            self.output_root, (os.path.relpath(path, self.channel_root))
        )

        output_temp_path = os.path.join(
            self.output_root, (os.path.relpath(temp_path, self.channel_root))
        )

        os.makedirs(os.path.dirname(output_temp_path), exist_ok=True)

        log.debug(f"_maybe_write {path} to {output_path}")

        return self._maybe_write_output_paths(
            content, output_path, output_temp_path, write_newline_end
        )

    def _maybe_write_output_paths(
        self, content: str | bytes, output_path, output_temp_path, write_newline_end
    ):
        """
        Internal to _maybe_write.
        """

        if isinstance(content, str):
            mode = "w"
            encoding = "utf-8"
            newline = "\n"
            newline_option = "\n"
        else:
            mode = "wb"
            encoding = None
            newline = b"\n"
            newline_option = None

        # XXX could we avoid writing output_temp_path in some cases?

        # always use \n line separator
        with open(
            output_temp_path,
            mode=mode,
            encoding=encoding,
            newline=newline_option,
        ) as fh:
            fh.write(content)
            if write_newline_end:
                fh.write(newline)

        if isfile(output_path):
            if utils.file_contents_match(output_temp_path, output_path):
                # No need to change mtimes. The contents already match.
                os.unlink(output_temp_path)
                return False

        utils.move_with_fallback_nolock(output_temp_path, output_path)
        return True

    def _maybe_remove(self, path):
        """
        Remove path if it exists, rewriting to respect self.output_root.
        """

        # intercept to support separate output_directory
        output_path = os.path.join(
            self.output_root, (os.path.relpath(path, self.channel_root))
        )

        log.debug(f"_maybe_remove {path} from {output_path}")

        if isfile(output_path):
            os.unlink(output_path)
