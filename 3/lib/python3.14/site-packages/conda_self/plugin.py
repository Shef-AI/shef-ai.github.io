"""Plugin hook implementations for conda-self."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.common.configuration import PrimitiveParameter, SequenceParameter
from conda.plugins.hookspec import hookimpl
from conda.plugins.types import CondaHealthCheck, CondaSetting, CondaSubcommand

from .cli import configure_parser, execute
from .constants import PERMANENT_PACKAGES, SELF_PERMANENT_PACKAGES_SETTING

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_subcommands() -> Iterable[CondaSubcommand]:
    """Expose the `self` subcommand."""
    yield CondaSubcommand(
        name="self",
        action=execute,
        configure_parser=configure_parser,
        summary="Manage conda and its plugins in the base environment.",
    )


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the base environment protection health check."""
    from .health_checks import base_protection

    yield CondaHealthCheck(
        name="base-protection",
        action=base_protection.check,
        fixer=base_protection.fix,
        summary="Check whether the base environment is marked as frozen",
        fix=(
            "Clone the base environment to 'default', reset it, and mark it as frozen"
        ),
    )


@hookimpl
def conda_settings() -> Iterable[CondaSetting]:
    """Register conda-self plugin settings."""
    yield CondaSetting(
        name=SELF_PERMANENT_PACKAGES_SETTING,
        description=(
            f"Additional packages, besides {', '.join(PERMANENT_PACKAGES)}, to "
            "retain with their dependencies in the current and installer-updated "
            "reset modes and protect from conda self remove. Exact snapshot modes "
            "and conda self remove --force may remove them."
        ),
        parameter=SequenceParameter(PrimitiveParameter("", element_type=str)),
    )
