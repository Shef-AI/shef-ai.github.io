# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Gather installer and conda resource attributes for telemetry."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conda import __version__ as conda_version
from conda.auxlib.type_coercion import boolify
from conda.base.context import context

#: Required fields in ``.installer.info``, as written by constructor
INSTALLER_INFO_FIELDS = ("name", "version", "platform", "type")

#: Subset of ``INSTALLER_INFO_FIELDS`` on the approved schema as attributes
INSTALLER_ATTRIBUTE_FIELDS = ("name", "version", "platform")

#: Maximum size of .installer.info that we parse.
#:  Note that as of today the file is usually 1-2KB.
INSTALLER_INFO_FILE_SIZE_LIMIT = 100 * 1024  # 100 KiB

#: Maximum length of each string field in .installer.info.
INSTALLER_INFO_FIELD_LENGTH_LIMIT = 256


def get_installer_attributes() -> dict[str, str]:
    """Read constructor's installer metadata from the base prefix.

    Returns an empty dict if ``.installer.info`` is missing, malformed, too
    large, or has a field that is too long, rather than raising.

    TODO: this duplicates conda's own conda.cli.main_info.get_installer_info(),
    which isn't available in the minimum conda version we support yet
    """
    path = Path(context.root_prefix, ".installer.info")
    try:
        if path.stat().st_size > INSTALLER_INFO_FILE_SIZE_LIMIT:
            return {}
        with path.open() as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}

    # Every required field must be a non-empty string that is not too long.
    # If any field fails, we return nothing instead of partial data.
    if not isinstance(data, dict) or any(
        not isinstance(data.get(field), str)
        or not data[field]
        or len(data[field]) > INSTALLER_INFO_FIELD_LENGTH_LIMIT
        for field in INSTALLER_INFO_FIELDS
    ):
        return {}

    return {f"installer.{field}": data[field] for field in INSTALLER_ATTRIBUTE_FIELDS}


def get_conda_attributes() -> dict[str, str]:
    """Gather all ``conda.*`` resource attributes.

    Some related attributes, such as ``python.version``, ``os.type``, and
    ``os.version``, are not gathered here since ``ResourceAttributes``
    already supplies them.

    Boolean values are JSON-encoded because ``ResourceAttributes.__setattr__()``
    converts dynamic scalar attributes with ``str()``, which would otherwise
    produce ``True`` or ``False`` instead of valid JSON.
    """
    return {
        "conda.version": conda_version,
        "conda.ci_detected": json.dumps(boolify(os.environ.get("CI", ""))),
    }
