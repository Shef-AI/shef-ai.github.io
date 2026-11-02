# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda channel's Terms of Service management plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

#: Application name.
APP_NAME: Final = "conda-anaconda-tos"

try:
    from ._version import __version__
except ImportError:
    # _version.py is only created after running `pip install`
    try:
        from setuptools_scm import get_version

        __version__ = get_version(root="..", relative_to=__file__)
    except (ImportError, OSError, LookupError):
        # ImportError: setuptools_scm isn't installed
        # OSError: git isn't installed
        # LookupError: setuptools_scm unable to detect version
        # conda-anaconda-tos follows SemVer, so the dev version is:
        #     MJ.MN.MICRO.devN+gHASH[.dirty]
        __version__ = "0.0.0.dev0+placeholder"

#: Application version.
APP_VERSION: Final = __version__
