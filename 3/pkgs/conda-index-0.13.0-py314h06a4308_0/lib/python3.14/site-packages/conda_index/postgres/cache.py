"""
Use sqlalchemy+postgresql instead of sqlite.
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import re
from typing import TYPE_CHECKING

import sqlalchemy
from psycopg2 import OperationalError
from sqlalchemy import cte, join, or_, select
from sqlalchemy.dialects.postgresql import insert

from ..index.cache import (
    BaseCondaIndexCache,
    IndexedPackages,
    IndexedShard,
    clear_newline_chars,
    pack_record,
)
from ..index.sqlitecache import (
    ICON_PATH,
    PATH_TO_TABLE,
    TABLE_NO_CACHE,
    cacher,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import Any

    from sqlalchemy import Connection

    from ..index.cache import ChangedPackage, HasChecksumsAndSize
    from ..index.fs import MinimalFS

from . import model

log = logging.getLogger(__name__)

# CEP 26 channel path component syntax. Prefix queries must use autoescape=True.
CHANNEL_ID_PATTERN = r"[a-z0-9_][a-z0-9_.-]*"

# XXX convert based on streaming "blob of json's to put in store()"

_engine = None


class PsqlCache(BaseCondaIndexCache):
    def __init__(
        self,
        channel_root: Path | str,
        subdir: str,
        *,
        fs: MinimalFS | None = None,
        channel_url: str | None = None,
        upstream_stage: str = "fs",
        include_stages: list[str] = [],
        db_url: str = "",
        **kwargs,
    ):
        super().__init__(
            channel_root,
            subdir,
            fs=fs,
            channel_url=channel_url,
            upstream_stage=upstream_stage,
            include_stages=include_stages,
            **kwargs,
        )
        self.db_filename = self.channel_root / ".cache" / "cache.json"
        self.db_url = db_url

        # each on-disk location gets a unique (random) prefix in the shared database
        if not self.db_filename.exists():
            self.db_filename.parent.mkdir(parents=True)
            self.db_filename.write_text(json.dumps({"channel_id": os.urandom(8).hex()}))
            self.cache_is_brand_new = True
        else:
            self.cache_is_brand_new = False

        self.channel_id = json.loads(self.db_filename.read_text())["channel_id"]
        if not re.fullmatch(CHANNEL_ID_PATTERN, self.channel_id):
            raise ValueError(
                f'{self.db_filename} contains invalid channel_id="{self.channel_id}"'
            )

    def __getstate__(self):
        """
        Remove db connection when pickled.
        """
        # probably no longer an issue since it is using a global _engine
        return {k: self.__dict__[k] for k in self.__dict__ if k not in ("engine",)}

    @property
    def database_prefix(self):
        """
        All paths must be prefixed with this string.
        """
        # If recording information about the channel_root, use '_ROOT' for nice
        # prefix searches
        return f"{self.channel_id}/{self.subdir or '_ROOT'}/"

    @cacher
    def engine(self):
        # Per-process module-scoped engine cache is one way to solve ProcessPool
        # "too many connections" issue
        global _engine
        if _engine:
            return _engine
        engine = sqlalchemy.create_engine(self.db_url, echo=False)
        model.create(engine)
        _engine = engine
        return engine

    def convert(self, force=False):
        """
        Load filesystem cache into database.
        """
        # or call model.create(engine) here?
        log.warning(f"{self.__class__}.convert() is not implemented")

    def store_stat_state(
        self, stage: str | None, listdir_stat: Iterable[dict[str, Any]]
    ):
        """
        Write {path, mtime, size} into database.
        """
        stage = stage or self.upstream_stage
        connection: Connection
        with self.engine.begin() as connection:
            stat = model.Stat.__table__

            if not self.update_only:
                connection.execute(
                    stat.delete().where(
                        stat.c.stage == stage,
                        stat.c.path.startswith(self.database_prefix, autoescape=True),
                    )
                )

            items = [{**item, "stage": stage} for item in listdir_stat]
            if items:
                insert_statement = insert(stat)
                connection.execute(
                    insert_statement.on_conflict_do_update(
                        index_elements=[stat.c.stage, stat.c.path],
                        set_={
                            "mtime": insert_statement.excluded.mtime,
                            "size": insert_statement.excluded.size,
                        },
                    ),
                    items,
                )

    def store(
        self,
        fn: str,
        size: int,
        mtime,
        members: dict[str, str | bytes],
        index_json: HasChecksumsAndSize,
    ):
        """
        Write cache for a single package to database.
        """
        database_path = self.database_path(fn)
        connection: Connection
        with self.engine.begin() as connection:
            for have_path in members:
                table: str = PATH_TO_TABLE[have_path]
                if table in TABLE_NO_CACHE or table == "index_json":
                    continue  # not cached, or for index_json cached at end

                table_obj = model.Base.metadata.tables[table]
                data_column = {"icon": "icon_png"}.get(table, table)
                parameters = {
                    "path": database_path,
                    data_column: members.get(have_path),
                }

                if have_path == ICON_PATH:
                    # not parsed as json
                    pass
                elif parameters[table] is not None:
                    # There will be an extra json.dumps() on the way to the
                    # database. May not be convenient to pass json text
                    # directly into the database's json parser for a small
                    # gain.
                    parameters[table] = json.loads(parameters[table])

                insert_obj = insert(table_obj)
                query = insert_obj.values(**parameters).on_conflict_do_update(
                    index_elements=[table_obj.c.path],
                    set_={data_column: insert_obj.excluded[data_column]},
                )
                # Could delete from all metadata tables that we didn't just see.
                try:
                    connection.execute(query)
                except OperationalError:  # e.g. malformed json.
                    log.exception("table=%s parameters=%s", table, parameters)
                    raise

            table = "index_json"
            index_json_table = model.Base.metadata.tables[table]
            insert_obj = insert(index_json_table)
            connection.execute(
                insert(index_json_table)
                .values(path=database_path, index_json=index_json)
                .on_conflict_do_update(
                    index_elements=[index_json_table.c.path],
                    set_={table: insert_obj.excluded.index_json},
                )  # it will cast to jsonb automatically
            )

            stat_table = model.Base.metadata.tables["stat"]
            values = {
                "path": database_path,
                "stage": "indexed",
                "mtime": mtime,
                "size": size,
                "sha256": index_json["sha256"],
                "md5": index_json["md5"],
            }
            stat_insert = insert(stat_table)
            connection.execute(
                stat_insert.on_conflict_do_update(
                    index_elements=[stat_table.c.path, stat_table.c.stage],
                    set_={
                        "mtime": stat_insert.excluded.mtime,
                        "size": stat_insert.excluded.size,
                        "sha256": stat_insert.excluded.sha256,
                        "md5": stat_insert.excluded.md5,
                    },
                ),
                values,
            )

    def changed_packages(self) -> list[ChangedPackage]:  # XXX or FileInfo dataclass
        """
        Compare upstream to 'indexed' state.

        Return packages in upstream that are changed or missing compared to 'indexed'.
        """

        stat_table = model.Stat.__table__
        stat_fs = cte(
            select(stat_table).where(stat_table.c.stage == self.upstream_stage),
            "stat_fs",
        )
        stat_indexed = cte(
            select(stat_table).where(stat_table.c.stage == "indexed"),
            "stat_indexed",
        )

        query = (
            select(stat_fs)
            .select_from(
                join(
                    stat_fs,
                    stat_indexed,
                    stat_fs.c.path == stat_indexed.c.path,
                    isouter=True,
                )
            )
            .where(stat_fs.c.path.startswith(self.database_prefix, autoescape=True))
            .where(
                or_(
                    stat_fs.c.mtime != stat_indexed.c.mtime,
                    stat_fs.c.size != stat_indexed.c.size,
                    stat_indexed.c.path == None,  # noqa: E711
                )
            )
        )

        connection: Connection
        with self.engine.begin() as connection:
            return [
                dict(path=row.path, size=row.size, mtime=row.mtime)
                for row in connection.execute(query)
            ]  # type: ignore

    def indexed_shards(
        self, desired: set[str] | None = None, *, pack_record=pack_record
    ) -> Iterator[IndexedShard]:
        """
        Yield (package name, all packages with that name) from database ordered
        by name, path i.o.w. filename.

        :param desired: If not None, set of desired package names.
        :param pack_record: Function passed each record, returning a modified
            record. Override to change the default hex to bytes hash
            conversions.
        """
        # not optimized for "desired" partial shards case but that's not
        # currently used.
        query = self._indexed_records_query(include_run_exports=True)

        connection: Connection
        with self.engine.begin() as connection:
            for name, rows in itertools.groupby(
                connection.execute(query),
                lambda k: k.name,
            ):
                shard_dict = {"packages": {}, "packages.conda": {}, "packages.whl": {}}
                shard = IndexedShard(
                    name=name,
                    packages=shard_dict["packages"],
                    packages_conda=shard_dict["packages.conda"],
                    packages_whl=shard_dict["packages.whl"],
                )
                for row in rows:
                    _, path, record, run_exports = row
                    record["run_exports"] = run_exports or {}
                    path = self.plain_path(path)

                    key = self.package_section_for_path(path)
                    if key is None:
                        log.warning("%s has unsupported extension", path)
                        continue
                    # This will be passed to the patch function, which we hope
                    # does not look for hex hash values.
                    shard_dict[key][path] = pack_record(record)

                if not desired or name in desired:
                    yield shard

    def _indexed_records_query(self, *, include_run_exports: bool):
        """
        Query package records from index_json + stat, optionally joining run_exports.
        """
        index_json_table = model.Base.metadata.tables["index_json"]
        stat_table = model.Base.metadata.tables["stat"]

        columns = [
            index_json_table.c.name,
            index_json_table.c.path,
            index_json_table.c.index_json,
        ]
        from_clause = join(
            index_json_table,
            stat_table,
            index_json_table.c.path == stat_table.c.path,
        )

        if include_run_exports:
            run_exports_table = model.Base.metadata.tables["run_exports"]
            columns.append(run_exports_table.c.run_exports)
            from_clause = join(
                from_clause,
                run_exports_table,
                index_json_table.c.path == run_exports_table.c.path,
                isouter=True,
            )

        check_stages = [self.upstream_stage] + self.include_stages
        return (
            select(*columns)
            .select_from(from_clause)
            .where(stat_table.c.stage.in_(check_stages))
            .where(stat_table.c.path.startswith(self.database_prefix, autoescape=True))
            .order_by(index_json_table.c.name, index_json_table.c.path)
        )

    def indexed_packages(self) -> IndexedPackages:
        """
        Return package sections from the cache.
        """
        shard_dict = {"packages": {}, "packages.conda": {}, "packages.whl": {}}

        query = self._indexed_records_query(include_run_exports=False)

        connection: Connection
        with self.engine.begin() as connection:
            for row in connection.execute(query):
                path = self.plain_path(row.path)
                key = self.package_section_for_path(path)
                if key is None:
                    log.warning("%s has unsupported extension", path)
                    continue
                shard_dict[key][path] = row.index_json

        return IndexedPackages(
            packages=shard_dict["packages"],
            packages_conda=shard_dict["packages.conda"],
            packages_whl=shard_dict["packages.whl"],
        )

    def load_all_from_cache(self, fn: str):
        """
        Load package data into a single dict for channeldata.

        :param fn: filename from channeldata.json; can be missing from database.
        """
        # XXX called in parallel by ChannelIndex(), easily exceeds postgresql connection limit
        connection: Connection
        with self.engine.begin() as connection:
            try:
                stat_table = model.Base.metadata.tables["stat"]
                row = connection.execute(
                    select(stat_table).where(
                        stat_table.c.stage == self.upstream_stage,
                        stat_table.c.path == self.database_path(fn),
                    )
                ).first()
                if not row:
                    raise KeyError(fn)
                mtime = row.mtime
            except KeyError:  # .fetchone() was None
                log.warning("%s mtime not found in cache", fn)
                return {}

            tables = model.Base.metadata.tables

            index_json = tables["index_json"]
            about = tables["about"]
            post_install = tables["post_install"]
            recipe = tables["recipe"]
            run_exports = tables["run_exports"]

            # This method reads up pretty much all of the cached metadata, except
            # for paths. It all gets dumped into a single map.

            BIG_JOIN = (
                index_json.join(
                    about,
                    isouter=True,
                    onclause=index_json.c.path == about.c.path,
                )
                .join(
                    post_install,
                    isouter=True,
                    onclause=index_json.c.path == post_install.c.path,
                )
                .join(
                    recipe,
                    isouter=True,
                    onclause=index_json.c.path == recipe.c.path,
                )
                .join(
                    run_exports,
                    isouter=True,
                    onclause=index_json.c.path == run_exports.c.path,
                )
            )

            row = connection.execute(
                select(BIG_JOIN).where(index_json.c.path == self.database_path(fn))
            ).first()

            if row is None:
                return {}

            data = {}

            # This order matches the old implementation. clobber recipe, about fields with index_json.
            for column in ("recipe", "about", "post_install", "index_json"):
                if column_data := getattr(row, column):  # is not null or empty
                    if not isinstance(column_data, dict):  # pragma: no cover
                        log.warning(f"scalar {column_data} found in {column} for {fn}")
                        continue
                    data.update(column_data)

            data["mtime"] = mtime

            source = data.get("source", {})
            try:
                data.update({"source_" + k: v for k, v in source.items()})
            except AttributeError:
                # sometimes source is a  list instead of a dict
                pass
            clear_newline_chars(data, "description")
            clear_newline_chars(data, "summary")

            # if run_exports was NULL / empty string, 'loads' the empty object
            data["run_exports"] = getattr(row, "run_exports", {}) if row else {}

        return data

    def run_exports(self) -> Iterator[tuple[str, dict]]:
        """
        Query returning run_exports data, to be formatted by
        ChannelIndex.build_run_exports_data()
        """
        stat = model.Base.metadata.tables["stat"]
        run_exports = model.Base.metadata.tables["run_exports"]
        index_json = model.Base.metadata.tables["index_json"]

        # only packages that are in stat *and* index_json
        query = select(
            stat.join(index_json, onclause=stat.c.path == index_json.c.path).join(
                run_exports, onclause=stat.c.path == run_exports.c.path, isouter=True
            )
        ).where(
            stat.c.stage == self.upstream_stage,
            stat.c.path.startswith(self.database_prefix, autoescape=True),
        )
        connection: Connection
        with self.engine.begin() as connection:
            for row in connection.execute(query):
                yield (self.plain_path(row.path), row.run_exports or {})
