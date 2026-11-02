"""
Updated command line interface for conda-index.
"""

from __future__ import annotations

import argparse
import logging
import os.path
import sys
from pathlib import Path

from .. import yaml
from ..index import MAX_THREADS_DEFAULT, ChannelIndex, logutil


def configure_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Configure the argument parser."""
    parser.description = (
        "Generate conda repository metadata (repodata.json) from a directory tree."
    )

    # Positional argument
    parser.add_argument(
        "dir",
        help="Directory to index",
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Output repodata to given directory.",
    )

    parser.add_argument(
        "--subdir",
        action="append",
        help="Subdir to index. Accepts multiple.",
    )

    parser.add_argument(
        "-n",
        "--channel-name",
        help="Customize the channel name listed in each channel's index.html.",
    )

    # Patch generator
    parser.add_argument(
        "--patch-generator",
        help="Path to Python file that outputs metadata patch instructions from its "
        "_patch_repodata function or a .tar.bz2/.conda file which contains a "
        "patch_instructions.json file for each subdir",
    )

    # Boolean flags for channeldata and RSS
    parser.add_argument(
        "--channeldata",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate channeldata.json. Conflicts with --no-write-monolithic.",
    )

    parser.add_argument(
        "--rss",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write rss.xml (Only if --channeldata is enabled).",
    )

    # Compression options
    parser.add_argument(
        "--bz2",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write repodata.json.bz2.",
    )

    parser.add_argument(
        "--zst",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write repodata.json.zst.",
    )

    # Run exports and compact
    parser.add_argument(
        "--run-exports",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write run_exports.json. Conflicts with --no-write-monolithic.",
    )

    parser.add_argument(
        "--compact",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Output JSON as one line, or pretty-printed.",
    )

    # Current index versions file
    parser.add_argument(
        "--current-index-versions-file",
        "-m",
        help="YAML file containing name of package as key, and list of versions as values. "
        "The current_index.json will contain the newest from this series of versions. "
        "For example: python: [3.8, 3.9] will keep python 3.8.X and 3.9.Y in the "
        "current_index.json, instead of only the very latest python version.",
    )

    # Base URL
    parser.add_argument(
        "--base-url",
        help="If packages should be served separately from repodata.json, URL of the "
        "directory tree holding packages. Generates repodata.json with "
        "repodata_version=2 which is supported in conda 24.5.0 or later.",
    )

    # Update cache and update only
    parser.add_argument(
        "--update-cache",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Control whether listdir() is called to refresh the set of available "
        "packages. Used to generate complete repodata.json from cache only when "
        "packages are not on disk. (Experimental)",
    )

    parser.add_argument(
        "--update-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Control whether missing files are deleted from repodata.json. Used to "
        "add local files to repodata.json without having the complete set of "
        "packages on disk. (Experimental)",
    )

    # Upstream stage
    parser.add_argument(
        "--upstream-stage",
        help="Set to 'clone' to generate example repodata from conda-forge test database. "
        "(Experimental)",
        default="fs",
    )

    # Current repodata
    parser.add_argument(
        "--current-repodata",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip generating current_repodata.json, a file containing only the newest "
        "versions of all packages and their dependencies, only used by the "
        "classic solver. Conflicts with --no-write-monolithic.",
    )

    # Threads and verbose
    parser.add_argument(
        "--threads",
        type=int,
        default=MAX_THREADS_DEFAULT,
        help="Number of threads to use",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    # Write monolithic and write shards
    parser.add_argument(
        "--write-monolithic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write repodata.json with all package metadata in a single file.",
    )

    parser.add_argument(
        "--write-shards",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write a repodata.msgpack.zst index and many smaller files per CEP-16.",
    )

    # Database options
    parser.add_argument(
        "--db",
        choices=["sqlite3", "postgresql"],
        default="sqlite3",
        help='Choose database backend. "sqlite3" (default) or "postgresql"',
    )

    parser.add_argument(
        "--db-url",
        default=os.environ.get("CONDA_INDEX_DBURL", "postgresql:///conda_index"),
        help="SQLAlchemy database URL when using --db=postgresql. Alternatively, use "
        "the CONDA_INDEX_DBURL environment variable.",
    )

    # HTML dependencies and repodata-next
    parser.add_argument(
        "--html-dependencies",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include dependency popups in generated HTML index files. "
        "May significantly increase file size for large repositories like "
        "main or conda-forge.",
    )

    parser.add_argument(
        "--repodata-next",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="EXPERIMENTAL. Write CEP-XXXX v3 repodata layout with all package "
        "records under a top-level v3 key.",
    )

    return parser


def _create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    return configure_parser(argparse.ArgumentParser(add_help=True))


def cli(args: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = _create_parser()
    run(parser.parse_args(args))


def run(parsed_args: argparse.Namespace) -> None:
    """Run the CLI from parsed arguments."""
    _main_impl(
        dir=parsed_args.dir,
        patch_generator=parsed_args.patch_generator,
        subdir=parsed_args.subdir,
        output=parsed_args.output,
        channeldata=parsed_args.channeldata,
        verbose=parsed_args.verbose,
        threads=parsed_args.threads,
        current_index_versions_file=parsed_args.current_index_versions_file,
        channel_name=parsed_args.channel_name,
        bz2=parsed_args.bz2,
        zst=parsed_args.zst,
        rss=parsed_args.rss,
        run_exports=parsed_args.run_exports,
        compact=parsed_args.compact,
        base_url=parsed_args.base_url,
        update_cache=parsed_args.update_cache,
        upstream_stage=parsed_args.upstream_stage,
        current_repodata=parsed_args.current_repodata,
        write_monolithic=parsed_args.write_monolithic,
        write_shards=parsed_args.write_shards,
        db=parsed_args.db,
        db_url=parsed_args.db_url,
        html_dependencies=parsed_args.html_dependencies,
        update_only=parsed_args.update_only,
        repodata_next=parsed_args.repodata_next,
    )


def _main_impl(
    dir: str,
    patch_generator: str | None = None,
    subdir: list[str] | None = None,
    output: str | None = None,
    channeldata: bool = False,
    verbose: bool = False,
    threads: int | None = None,
    current_index_versions_file: str | None = None,
    channel_name: str | None = None,
    bz2: bool = False,
    zst: bool = False,
    rss: bool = False,
    run_exports: bool = False,
    compact: bool = True,
    base_url: str | None = None,
    update_cache: bool = False,
    upstream_stage: str = "fs",
    current_repodata: bool = True,
    write_monolithic: bool = True,
    write_shards: bool = False,
    db: str = "sqlite3",
    db_url: str = "",
    html_dependencies: bool = False,
    update_only: bool = False,
    repodata_next: bool = False,
) -> None:
    """Implementation of the main CLI logic."""
    logutil.configure()
    if verbose:
        logging.getLogger("conda_index.index").setLevel(logging.DEBUG)

    if output:
        output = os.path.expanduser(output)

    if not write_monolithic:
        # --current-repodata, --run-exports, and --channeldata are only supported with --write-monolithic
        incompatible_args = []
        if current_repodata:
            incompatible_args.append("--current-repodata")
        if run_exports:
            incompatible_args.append("--run-exports")
        if channeldata:
            incompatible_args.append("--channeldata")

        if incompatible_args:
            args_str = ", ".join(incompatible_args)
            error_msg = f"Conflicting arguments: {args_str} require(s) --write-monolithic (the default setting)."
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

    cache_kwargs = {}

    if db == "postgresql":
        try:
            from ..postgres.cache import PsqlCache

            cache_class = PsqlCache
            cache_kwargs["db_url"] = db_url
        except ImportError as e:
            error_msg = f"Missing dependencies for postgresql: {e}"
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
    else:
        from ..index.sqlitecache import CondaIndexCache

        cache_class = CondaIndexCache

    channel_index = ChannelIndex(
        os.path.expanduser(dir),
        channel_name=channel_name,
        output_root=output,
        subdirs=subdir,
        write_bz2=bz2,
        write_zst=zst,
        threads=threads,
        write_run_exports=run_exports,
        compact_json=compact,
        base_url=base_url,
        save_fs_state=update_cache,
        write_current_repodata=current_repodata,
        upstream_stage=upstream_stage,
        write_monolithic=write_monolithic,
        write_shards=write_shards,
        cache_class=cache_class,
        cache_kwargs=cache_kwargs,
        html_dependencies=html_dependencies,
        update_only=update_only,
        repodata_v3=repodata_next,
    )

    if update_cache is False:
        # We call listdir() in save_fs_state, or its remote fs equivalent; then
        # we call changed_packages(); but the changed_packages query against a
        # remote filesystem is different than the one we need for a local
        # filesystem. How about skipping the extract packages stage entirely by
        # returning no changed packages? Might fail if we use
        # threads/multiprocessing.
        def no_changed_packages(self, *args):
            return []

        # We'll want to restore this method after indexing, so save the original.
        original_changed_packages = channel_index.cache_class.changed_packages
        channel_index.cache_class.changed_packages = no_changed_packages

    try:
        current_index_versions = None
        if current_index_versions_file:
            with open(current_index_versions_file) as f:
                current_index_versions = yaml.safe_load(f)

        if patch_generator:
            patch_generator = str(Path(patch_generator).expanduser())

        channel_index.index(
            patch_generator=patch_generator,  # or will use outdated .py patch functions
            current_index_versions=current_index_versions,
            progress=False,  # clone is a batch job
        )
    finally:
        if update_cache is False:
            # Restore the original changed_packages method after indexing.
            channel_index.cache_class.changed_packages = original_changed_packages

    if channeldata:  # about 2 1/2 minutes for conda-forge
        channel_index.update_channeldata(rss=rss)
