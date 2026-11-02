from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from ..constants import RESET_FILE_BASE_PROTECTION, RESET_FILE_INSTALLER

if TYPE_CHECKING:
    import argparse


class Snapshot(Enum):
    """Snapshot modes accepted by ``conda self reset --snapshot``.

    Plain :class:`enum.Enum` for Python 3.10 compatibility. The string values
    double as argparse choices and user-facing mode names. Switch to
    :class:`enum.StrEnum` when 3.11 becomes the minimum supported version
    (mirrors the TODO on conda's ``EnvironmentFormat``).
    """

    CURRENT = "current"
    INSTALLER = "installer"  # Accepted only to explain how to migrate.
    INSTALLER_EXACT = "installer-exact"
    INSTALLER_UPDATED = "installer-updated"
    BASE_PROTECTION = "base-protection"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        match self:
            case Snapshot.CURRENT:
                return "current"
            case Snapshot.INSTALLER:
                return "installer"
            case Snapshot.INSTALLER_EXACT:
                return "installer-provided (exact)"
            case Snapshot.INSTALLER_UPDATED:
                return "installer-provided (with updates)"
            case Snapshot.BASE_PROTECTION:
                return "base-protection"

    @property
    def file_path(self) -> Path | None:
        """The ``conda-meta/*.txt`` file this snapshot mode reads, if any."""
        match self:
            case Snapshot.INSTALLER_EXACT | Snapshot.INSTALLER_UPDATED:
                return Path(sys.prefix, "conda-meta", RESET_FILE_INSTALLER)
            case Snapshot.BASE_PROTECTION:
                return Path(sys.prefix, "conda-meta", RESET_FILE_BASE_PROTECTION)
            case Snapshot.CURRENT | Snapshot.INSTALLER:
                return None


# Tried in order when --snapshot is not provided. The first mode whose file
# exists on disk wins, otherwise we fall through to CURRENT.
FALLBACK_ORDER: tuple[Snapshot, ...] = (
    Snapshot.BASE_PROTECTION,
    Snapshot.INSTALLER_UPDATED,
)


HELP = "Reset the base environment."
SNAPSHOT_HELP = dedent(
    """
    Reset mode for the base environment.
    `current` removes all conda packages except for `conda`, `conda-self`,
    installed conda plugins, configured permanent packages, and their
    dependencies.
    `installer-exact` restores exactly the conda packages recorded by the
    installer and may downgrade updated packages.
    `installer-updated` retains the packages kept by `current` and currently
    installed conda packages whose names appear in the installer snapshot. It
    does not update packages or install missing packages.
    `base-protection` restores exactly the conda packages recorded by
    `conda doctor -n base base-protection --fix` before protecting base.
    The old `installer` spelling is rejected with migration guidance. Choose
    `installer-exact` or `installer-updated` explicitly.

    If not set, `conda self` selects `base-protection` when its snapshot file
    exists, otherwise `installer-updated` when the installer snapshot file
    exists, and otherwise `current`.
    """
).lstrip()

WHAT_TO_EXPECT_CURRENT = dedent(
    """
    This resets the base environment to keep conda, conda-self, installed conda
    plugins, configured permanent packages, and their dependencies.
    All other conda packages are removed.
    """
).lstrip()
WHAT_TO_EXPECT_SNAPSHOT = dedent(
    """
    This resets the base environment using the '{mode_name}' mode
    and removes conda packages not retained by that mode.
    """
).lstrip()
SUCCESS = "Reset the base environment using the 'current' mode.\n"
SUCCESS_SNAPSHOT = "Reset the base environment using the '{mode_name}' mode.\n"


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--snapshot",
        type=Snapshot,
        choices=list(Snapshot),
        help=SNAPSHOT_HELP,
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context
    from conda.cli.common import stdout_json_success
    from conda.exceptions import CondaValueError
    from conda.reporters import confirm_yn

    from ..query import permanent_dependencies
    from ..reset import names_from_explicit, reset

    snapshot: Snapshot | None = args.snapshot
    if snapshot is Snapshot.INSTALLER:
        raise CondaValueError(
            "The '--snapshot installer' mode is no longer supported. "
            "Use '--snapshot installer-exact' to restore the exact conda packages "
            "recorded by the installer, or '--snapshot installer-updated' to keep "
            "currently installed installer packages, conda plugins, and permanent "
            "packages with their dependencies. 'installer-updated' does not update "
            "packages or install missing packages. No reset was performed."
        )
    reset_file: Path | None = None

    if snapshot is not None:
        reset_file = snapshot.file_path
    else:
        for fallback in FALLBACK_ORDER:
            candidate = fallback.file_path
            if candidate is not None and candidate.exists():
                snapshot = fallback
                reset_file = candidate
                break

    if reset_file is not None and not reset_file.exists():
        raise FileNotFoundError(
            f"Snapshot file for the '{snapshot}' reset mode not found: {reset_file}"
        )

    if not context.json and not context.quiet:
        if snapshot is not None:
            print(WHAT_TO_EXPECT_SNAPSHOT.format(mode_name=snapshot.display_name))
        else:
            print(WHAT_TO_EXPECT_CURRENT)

    prompt = "Proceed with resetting the base environment"
    if snapshot is not None:
        prompt += f" using the '{snapshot.display_name}' mode"
    confirm_yn(f"{prompt}?[y/n]:\n", default="no", dry_run=context.dry_run)

    if not context.json and not context.quiet:
        print("Resetting the base environment...")

    match snapshot:
        case Snapshot.INSTALLER_UPDATED if reset_file is not None:
            keep = permanent_dependencies(add_plugins=True) | names_from_explicit(
                reset_file
            )
            reset(uninstallable_packages=keep)
        case Snapshot.INSTALLER_EXACT | Snapshot.BASE_PROTECTION:
            reset(snapshot=reset_file)
        case _:
            reset(uninstallable_packages=permanent_dependencies(add_plugins=True))

    if context.json:
        stdout_json_success()
    elif not context.quiet:
        if snapshot is not None:
            print(SUCCESS_SNAPSHOT.format(mode_name=snapshot.display_name))
        else:
            print(SUCCESS)

    return 0
