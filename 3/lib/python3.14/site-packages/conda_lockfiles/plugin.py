from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl
from conda.plugins.types import (
    CondaEnvironmentExporter,
    CondaEnvironmentSpecifier,
    EnvironmentFormat,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_environment_specifiers() -> Iterable[CondaEnvironmentSpecifier]:
    from .conda_lock import v1 as conda_lock_v1
    from .rattler_lock import v6 as rattler_lock_v6

    yield CondaEnvironmentSpecifier(
        name=conda_lock_v1.FORMAT,
        aliases=conda_lock_v1.ALIASES,
        default_filenames=conda_lock_v1.DEFAULT_FILENAMES,
        environment_spec=conda_lock_v1.CondaLockV1Loader,
        description="Multi-platform lockfile format with exact package versions",
        environment_format=EnvironmentFormat.lockfile,
    )
    yield CondaEnvironmentSpecifier(
        name=rattler_lock_v6.FORMAT,
        aliases=rattler_lock_v6.ALIASES,
        default_filenames=rattler_lock_v6.DEFAULT_FILENAMES,
        environment_spec=rattler_lock_v6.RattlerLockV6Loader,
        description="Rattler-based lockfile format from pixi",
        environment_format=EnvironmentFormat.lockfile,
    )


@hookimpl
def conda_environment_exporters() -> Iterable[CondaEnvironmentExporter]:
    from .conda_lock import v1 as conda_lock_v1
    from .rattler_lock import v6 as rattler_lock_v6

    yield CondaEnvironmentExporter(
        name=conda_lock_v1.FORMAT,
        aliases=conda_lock_v1.ALIASES,
        default_filenames=conda_lock_v1.DEFAULT_FILENAMES,
        multiplatform_export=conda_lock_v1.multiplatform_export,
        description="Multi-platform lockfile format with exact package versions",
        environment_format=EnvironmentFormat.lockfile,
    )
    yield CondaEnvironmentExporter(
        name=rattler_lock_v6.FORMAT,
        aliases=rattler_lock_v6.ALIASES,
        default_filenames=rattler_lock_v6.DEFAULT_FILENAMES,
        multiplatform_export=rattler_lock_v6.multiplatform_export,
        description="Rattler-based lockfile format from pixi",
        environment_format=EnvironmentFormat.lockfile,
    )
