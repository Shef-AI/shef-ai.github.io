"""
SQLAlchemy model for conda-index, following the pattern in convert_cache.py

Used for psqlcache mode instead of low-dependencies sqlite mode.
"""

from __future__ import annotations

from sqlalchemy import TEXT, Column, Computed, Integer, LargeBinary, Table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column

from ..index.cache import IndexedStages

TABLE_NAMES = {
    "about",
    "icon",
    "index_json",
    "post_install",
    "recipe",
    "run_exports",
}


class Base(DeclarativeBase):
    pass


metadata_obj = Base.metadata

for table in TABLE_NAMES:
    columns = []
    if table == "icon":
        columns.append(Column("icon_png", LargeBinary))
    else:
        columns.append(Column(table, JSONB))  # or JSONB for postgresql?
    if table == "index_json":
        columns.extend(
            (
                Column(
                    "name",
                    TEXT,
                    Computed(text("jsonb_extract_path_text(index_json, 'name')")),
                ),
                Column(
                    "sha256",
                    TEXT,
                    Computed(text("jsonb_extract_path_text(index_json, 'sha256')")),
                ),
            )
        )
    Table(table, metadata_obj, Column("path", TEXT, primary_key=True), *columns)


class Stat(Base):
    __table__: Table
    __tablename__ = "stat"

    stage = mapped_column(
        TEXT,
        default=IndexedStages.INDEXED_STAGE.value,
        nullable=False,
        primary_key=True,
    )
    path = mapped_column(TEXT, nullable=False, primary_key=True)
    mtime = mapped_column(Integer)
    size = mapped_column(Integer)
    sha256 = mapped_column(TEXT)
    md5 = mapped_column(TEXT)
    last_modified = mapped_column(TEXT)
    etag = mapped_column(TEXT)


def create(engine):
    """
    Create schema. Safe to call on every connection.
    """
    metadata_obj.create_all(engine)
