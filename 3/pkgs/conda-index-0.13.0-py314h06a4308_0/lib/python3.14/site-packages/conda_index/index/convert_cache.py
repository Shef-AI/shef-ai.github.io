"""
Given a conda <subdir>/.cache directory or a .tar.bz2 of that directory,

Create a sqlite database with the same data.

Intended to be used as a transition between the older format and a newer version
of `conda-build index`, or as the foundation of a package database.
"""

import json
import logging
import os
import os.path
import re
import sqlite3
from itertools import chain, islice

from . import common
from .cache import IndexedStages

log = logging.getLogger(__name__)

# maximum 'PRAGMA user_version' we support
USER_VERSION = 2

PATH_INFO = re.compile(
    r"""
    (?P<channel>[^/]*)/
    (?P<subdir>[^/]*)/
    .cache/
    (?P<path>(stat.json|
        (?P<kind>recipe|index|icon|about|recipe_log|run_exports|post_install)/(?P<basename>\S*?)(?P<ext>.\w+$))
    )""",
    re.VERBOSE,
)

# Finds directories like these, we are only concerned with {subdir}/.cache/*
TYPICAL_DIRECTORIES = {
    "",
    "clones/conda-forge/linux-64/.cache/recipe",
    "clones/conda-forge/linux-64",
    "clones/conda-forge/linux-64/.cache/index",
    "clones/conda-forge/linux-64/.cache/icon",  # only a dozen packages have icons
    "clones/conda-forge/linux-64/.cache",  # stat.json
    "clones/conda-forge",
    "clones/conda-forge/linux-64/.cache/about",
    "clones/conda-forge/linux-64/.cache/recipe_log",  # 100% empty {}'s
    "clones/conda-forge/linux-64/.cache/run_exports",  # mostly empty {}'s
    "clones",
    "clones/conda-forge/linux-64/.cache/post_install",
}

TABLE_NAMES = [
    "about",
    "icon",
    "index_json",
    "post_install",
    "recipe_log",
    "recipe",
    "run_exports",
]


def create(conn):
    """
    Create schema. Safe to call on every connection.
    """
    # BLOB columns are a little faster to LENGTH(col), returning number of
    # bytes instead of number of (possibly multi-byte utf-8) characters
    conn.execute("CREATE TABLE IF NOT EXISTS about (path TEXT PRIMARY KEY, about BLOB)")
    # index is a sql keyword
    # generated columns pulling fields from index_json could be nice
    # has md5, shasum. older? packages do not include timestamp?
    # SELECT path, datetime(json_extract(index_json, '$.timestamp'), 'unixepoch'), index_json from index_json
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS index_json (
            path TEXT PRIMARY KEY, index_json BLOB,
            name AS (json_extract(index_json, '$.name')),
            sha256 AS (json_extract(index_json, '$.sha256'))
        )
        """
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS recipe (path TEXT PRIMARY KEY, recipe BLOB)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS recipe_log (path TEXT PRIMARY KEY, recipe_log BLOB)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS run_exports (path TEXT PRIMARY KEY, run_exports BLOB)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS post_install (path TEXT PRIMARY KEY, post_install BLOB)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS icon (path TEXT PRIMARY KEY, icon_png BLOB)"
    )
    # Stat data. Compare to other tables, on-disk mtimes to see what's changed.
    #   "arrow-cpp-1.0.1-py310h33a019f_53_cuda.tar.bz2": {
    #     "mtime": 1636410074,
    #     "size": 22088344
    #   },
    # DATETIME(mtime, 'unixepoch')
    # May or may not need all these columns
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS stat (
                stage TEXT NOT NULL DEFAULT '{IndexedStages.INDEXED_STAGE.value}',
                path TEXT NOT NULL,
                mtime NUMBER,
                size INTEGER,
                sha256 TEXT,
                md5 TEXT,
                last_modified TEXT,
                etag TEXT
            )"""
    )

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_stat ON stat (path, stage)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stat_stage ON stat (stage, path)")


def migrate(conn):
    """
    Call on every connection to ensure we have the correct schema.

    Call inside a transaction.
    """
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]

    if user_version > USER_VERSION:
        raise ValueError(
            f"conda-index cache is too new: version {user_version} > {USER_VERSION}"
        )

    if user_version < 1:
        remove_prefix(conn)
        # PRAGMA can't accept ?-substitution
        conn.execute("PRAGMA user_version=1")

    if user_version < 2:
        add_computed_name(conn)
        conn.execute("PRAGMA user_version=2")


def remove_prefix(conn: sqlite3.Connection):
    """
    Store bare filenames in database instead of {channel}/{subdir}/{fn}

    Could add a view or a virtual column to restore globally-unique paths.

    Call inside a transaction.
    """

    log.info("Migrate database")

    def basename(path):
        if not isinstance(path, str):  # pragma: no cover
            # if our custom sqlite function is passed a non-str field
            return path
        return path.rsplit("/")[-1]

    conn.create_function("migrate_basename", 1, basename, deterministic=True)

    for table in TABLE_NAMES + ["stat"]:
        conn.execute(
            f"UPDATE OR IGNORE {table} SET path=migrate_basename(path) WHERE INSTR(path, '/')"
        )


def add_computed_name(db: sqlite3.Connection):
    """
    Add helpful computed columns to index_json.
    """
    columns = set(row[1] for row in db.execute("PRAGMA table_xinfo(index_json)"))
    if "name" not in columns:
        db.execute(
            "ALTER TABLE index_json ADD COLUMN name AS (json_extract(index_json, '$.name'))"
        )
    if "sha256" not in columns:
        db.execute(
            "ALTER TABLE index_json ADD COLUMN sha256 AS (json_extract(index_json, '$.sha256'))"
        )


def extract_cache_filesystem(path):
    """
    Yield interesting (match, <bytes>) members of filesystem at path.

    path should be an individual cache directory, e.g. <channel-name>/linux-64/.cache
    """
    assert str(path).endswith(".cache"), f"{path} must end with .cache"
    for root, _, files in os.walk(path):
        log.info(f"CONVERT {os.path.basename(root)}")
        for file in files:
            fullpath = os.path.join(root, file)
            posixpath = "/".join(fullpath.split(os.sep))
            path_info = PATH_INFO.search(posixpath)
            if path_info:
                try:
                    with open(fullpath, "rb") as entry:
                        yield path_info, entry
                except PermissionError as e:  # pragma: no cover
                    log.warning("Permission error: %s %s", fullpath, e)


# regex excludes arbitrary names
TABLE_MAP = {"index": "index_json"}

CHUNK_SIZE = 4096  # packages * cache folders = cache files


def db_path(match, override_channel=None):
    """
    Convert match to a database primary key. Retain the option to implement
    globally unique keys.
    """
    return f"{match['basename']}"


def ichunked(iterable, n):
    """
    Break iterable into n-item iterables.

    Lazier than Python 3.12 batched().
    """
    source = iter(iterable)
    for item in source:
        yield islice(chain([item], source), n)


def convert_cache(conn, cache_generator):
    """
    Convert old style `conda index` cache to sqlite cache.

    conn: sqlite3 connection
    cache_generator: extract_cache() or extract_cache_filesystem()
    override_channel: if channel_name is not in path

    Commits own transactions.
    """
    # chunked must be as lazy as possible to prevent tar seeks
    for i, chunk in enumerate(ichunked(cache_generator, CHUNK_SIZE)):
        log.info(f"BEGIN BATCH {i}")
        with conn:  # transaction
            for match, member in chunk:
                if match["path"] == "stat.json":
                    # stat.json is one file with information on all the
                    # packages, so we delete from stat.
                    conn.execute(
                        f"DELETE FROM stat WHERE stage='{IndexedStages.INDEXED_STAGE.value}'"
                    )
                    for key, value in json.load(member).items():
                        value["path"] = key
                        conn.execute(
                            f"INSERT OR REPLACE INTO stat (path, mtime, size, stage) VALUES (:path, :mtime, :size, '{IndexedStages.INDEXED_STAGE.value}')",
                            value,
                        )

                elif match["ext"] == ".json":
                    # {'channel': 'conda-forge', 'subdir': 'linux-64', 'path':
                    # 'post_install/vim-8.2.2905-py36he996604_0.tar.bz2.json',
                    # 'kind': 'post_install', 'basename':
                    # 'vim-8.2.2905-py36he996604_0.tar.bz2', 'ext': '.json'}
                    table = TABLE_MAP.get(match["kind"], match["kind"])
                    try:
                        conn.execute(
                            f"""
                        INSERT OR IGNORE INTO {table} (path, {table})
                        VALUES (:path, json(:data))
                        """,
                            {
                                "path": db_path(match),
                                "data": member.read(),
                            },
                        )
                    except sqlite3.OperationalError as e:
                        log.warning("SQL error. Not JSON? %s %s", match.groups(0), e)

                elif match["kind"] == "icon":
                    conn.execute(
                        """
                    INSERT OR IGNORE INTO icon (path, icon_png)
                    VALUES (:path, :data)
                    """,
                        {
                            "path": db_path(match),
                            "data": member.read(),
                        },
                    )

                else:  # pragma: no cover
                    log.warning("Unhandled %r", match.groupdict())


def merge_index_cache(channel_root, output_db="merged.db"):
    """
    Combine {channel_root}/*/.cache/cache.db databases into a single database.
    Useful for queries. Not used by any part of the indexing process.
    """
    from ..utils import DEFAULT_SUBDIRS

    channel_name = os.path.basename(channel_root)
    log.info(f"Merge caches for channel {channel_name}")
    combined_db = common.connect(output_db)
    with combined_db:
        create(combined_db)  # skip 'remove prefix' migration
    for subdir in DEFAULT_SUBDIRS:
        cache_db = os.path.join(channel_root, subdir, ".cache", "cache.db")
        if not os.path.exists(cache_db):
            continue
        channel_prefix = f"{channel_name}/{subdir}/"
        log.info(
            f"Merge {os.path.relpath(cache_db, os.path.dirname(channel_root))} as {channel_prefix}"
        )
        combined_db.execute("ATTACH DATABASE ? AS subdir", (cache_db,))

        for table in TABLE_NAMES:
            # does sqlite do less work explicity avoiding "replace when row
            # would not have changed"
            column = {"icon": "icon_png"}.get(table, table)
            if table == "icon":  # very rare
                continue
            query = f"""INSERT INTO main.{table} (path, {column})
            SELECT ? || path, {column} FROM subdir.{table} WHERE true -- avoid syntax ambiguity
            ON CONFLICT (path) DO UPDATE SET {column} = excluded.{column}
            WHERE {column} != excluded.{column} -- does this avoid work
            """
            try:
                with combined_db:
                    combined_db.execute(query, (channel_prefix,))
            except sqlite3.OperationalError:  # pragma: no cover
                log.error("OperationalError on %s", query)
                raise

        combined_db.execute("DETACH DATABASE subdir")
