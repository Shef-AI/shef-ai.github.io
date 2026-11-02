"""Queries for package dependency information."""

from __future__ import annotations

import sys
from contextlib import suppress

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.prefix_graph import PrefixGraph

from .constants import PERMANENT_PACKAGES, SELF_PERMANENT_PACKAGES_SETTING
from .exceptions import NoDistInfoDirFound
from .package_info import PackageInfo


def permanent_dependencies(add_plugins: bool = False) -> set[str]:
    """Get the full list of dependencies for all the permanent packages."""
    # In some dev environments, conda-self is installed as a PyPI package
    # and does not have its conda-meta/conda-self-*.json entry, which makes it
    # invisible to PrefixData()... unless we enable interoperability.
    installed = list(PrefixData(sys.prefix, interoperability=True).iter_records())
    prefix_graph = PrefixGraph(installed)

    protect = [
        *PERMANENT_PACKAGES,
        *getattr(context.plugins, SELF_PERMANENT_PACKAGES_SETTING),
    ]

    if add_plugins:
        for record in installed:
            with suppress(NoDistInfoDirFound):
                if any(
                    "conda" in pkg_info.entry_points()
                    for pkg_info in PackageInfo.from_record(record)
                ):
                    protect.append(record.name)

    packages = []
    for pkg in protect:
        node = next((rec for rec in prefix_graph.records if rec.name == pkg), None)
        if node:
            packages.append(node.name)
            packages.extend(
                [record.name for record in prefix_graph.all_ancestors(node)]
            )
    return set(packages)
