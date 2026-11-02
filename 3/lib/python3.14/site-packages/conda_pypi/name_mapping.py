"""PyPI ↔ conda package name mapping.

The default table is ``grayskull_pypi_mapping.json`` (regro/grayskull). Keys are
canonical PyPI names, resolved the same way as the table via
:func:`packaging.utils.canonicalize_name`.

When a name is missing from the table, the conda name is derived from the
original string: lowercase, underscores become hyphens, dots are unchanged.
That often matches conda-forge dotted packages; canonical form alone would map
``jaraco.tidelift`` to ``jaraco-tidelift``.

Grayskull (or a custom dict for :func:`pypi_to_conda_name`) is still required
when the conda package name does not follow that rule, for example
``typing-extensions`` → ``typing_extensions``.
"""

from __future__ import annotations

import json
import pkgutil

from packaging.utils import canonicalize_name

grayskull_pypi_mapping: dict[str, dict] = json.loads(
    pkgutil.get_data("conda_pypi", "grayskull_pypi_mapping.json") or "{}"
)

default_pypi_mapping: dict[str, dict] = dict(grayskull_pypi_mapping)

_to_pypi_name_map: dict[str, dict] = {}


def _unmapped_conda_name(pypi_name: str) -> str:
    return pypi_name.strip().lower().replace("_", "-")


def pypi_to_conda_name(pypi_name: str, pypi_to_conda_name_mapping: dict | None = None) -> str:
    raw = pypi_name.strip()
    key = canonicalize_name(raw)
    table = (
        pypi_to_conda_name_mapping
        if pypi_to_conda_name_mapping is not None
        else default_pypi_mapping
    )
    entry = table.get(key)
    if entry is not None:
        return entry["conda_name"]
    return _unmapped_conda_name(raw)


def conda_to_pypi_name(name: str) -> str:
    if not _to_pypi_name_map:
        for value in default_pypi_mapping.values():
            conda_name = value["conda_name"]
            # XXX sometimes conda:pypi is n:1
            _to_pypi_name_map[conda_name] = value

    found = _to_pypi_name_map.get(name)
    if found:
        name = found["pypi_name"]
    return canonicalize_name(name)
