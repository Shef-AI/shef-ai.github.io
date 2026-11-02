from __future__ import annotations

import configparser
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from conda.models.records import PrefixRecord

from .exceptions import NoDistInfoDirFound

if TYPE_CHECKING:
    from conda.models.records import PackageCacheRecord


# This is required for reading entry point info from an extracted package
# ref: https://packaging.python.org/en/latest/specifications/entry-points/#file-format
class CaseSensitiveConfigParser(configparser.ConfigParser):
    optionxform = staticmethod(str)


class PackageInfo:
    def __init__(self, dist_info_path: Path):
        """Describe the dist-info for a Python package installed as a conda package"""
        self.dist_info_path = dist_info_path

    @classmethod
    def read_manifest(cls, pkg_dir: str) -> list[str]:
        """Read file paths from an extracted package directory.

        Tries info/paths.json first (canonical per CEP), then falls back
        to info/files (deprecated legacy format).
        """
        pkg_path = Path(pkg_dir)

        paths_json = pkg_path / "info" / "paths.json"
        if paths_json.is_file():
            data = json.loads(paths_json.read_text())
            return [entry["_path"] for entry in data.get("paths", [])]

        try:
            return (pkg_path / "info" / "files").read_text().splitlines()
        except FileNotFoundError:
            return []

    @classmethod
    def from_record(
        cls, record: PrefixRecord | PackageCacheRecord
    ) -> list[PackageInfo]:
        had_manifest = True
        if not (paths := getattr(record, "files", None)):
            paths = cls.read_manifest(record.extracted_package_dir)
            had_manifest = bool(paths)
        dist_infos = set()
        for path in paths:
            if (maybe_dist_info := os.path.dirname(path)).endswith(".dist-info"):
                dist_infos.add(maybe_dist_info)
        if isinstance(record, PrefixRecord):
            basedir = sys.prefix
        else:
            basedir = record.extracted_package_dir

        if not dist_infos and not had_manifest and not isinstance(record, PrefixRecord):
            # Last resort for package cache records: scan the extracted
            # directory for .dist-info (e.g. bare wheel with no conda metadata).
            # Not safe for PrefixRecord where basedir is the entire prefix.
            basepath = Path(basedir)
            for candidate in basepath.rglob("*.dist-info"):
                if candidate.is_dir():
                    dist_infos.add(str(candidate.relative_to(basepath)))

        if not dist_infos:
            raise NoDistInfoDirFound(record.name, basedir)
        return [cls(Path(basedir, p)) for p in dist_infos]

    def entry_points(self) -> dict[str, dict[str, str]]:
        """Get the entry points for a package.

        The return value for this function has the form:

        {
            entry_point_group:{
                name: entry_point,
                . . .
            }
            . . .
        }

        :returns: a dictionary of entry point groups and the corresponding entry points
                  expressed as a dict.

        ref: https://packaging.python.org/en/latest/specifications/entry-points/#file-format
        """
        entry_point_file = self.dist_info_path / "entry_points.txt"
        entry_points_config = CaseSensitiveConfigParser()
        entry_points_config.read(entry_point_file)

        entry_points = {}
        for section in entry_points_config.sections():
            entry_points[section] = dict(entry_points_config[section])

        return entry_points
