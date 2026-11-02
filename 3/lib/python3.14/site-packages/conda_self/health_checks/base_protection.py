"""Health check: Base environment protection.

Checks if the base environment is protected (frozen) and offers to
protect it by cloning to a default environment and resetting base.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from conda.base.constants import OK_MARK, PREFIX_FROZEN_FILE, X_MARK
from conda.core.prefix_data import PrefixData

if TYPE_CHECKING:
    from argparse import Namespace

    from conda.plugins.types import ConfirmCallback


BASE_PROTECTION_FROZEN_MESSAGE = """\
Your base environment is protected from direct modifications.

To manage conda and its plugins, use conda self:
  conda self --help"""


def is_base_environment(prefix: str) -> bool:
    """Check if the given prefix is the base environment."""
    return prefix == sys.prefix


def is_base_protected() -> bool:
    """Check if the base environment is protected (frozen)."""
    frozen_file = PrefixData(sys.prefix).prefix_path / PREFIX_FROZEN_FILE
    return frozen_file.exists()


def check(prefix: str, _verbose: bool) -> None:
    """Health check: Verify base environment protection status.

    Only runs when checking the base environment.
    """
    if not is_base_environment(prefix):
        print("Skipping base protection: not running on the base environment.\n")
        return

    if is_base_protected():
        print(f"{OK_MARK} Base environment is marked as frozen.\n")
    else:
        print(f"{X_MARK} Base environment is not marked as frozen.\n")
        print("Run 'conda doctor -n base base-protection --fix' to protect it.\n")


def fix(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    """Fix: Protect the base environment.

    This clones the base environment to a new 'default' environment,
    removes conda packages not retained by base protection, and marks it as
    frozen.
    """
    from pathlib import Path

    from conda.base.context import context

    from ..constants import DEFAULT_ENV_NAME

    if not is_base_environment(prefix):
        print("Skipping: not running on the base environment.")
        return 0

    if is_base_protected():
        print("Base environment is already protected.")
        return 0

    import io
    import json
    from contextlib import nullcontext, redirect_stdout

    from conda.cli.condarc import ConfigurationFile
    from conda.exceptions import CondaOSError, CondaValueError
    from conda.gateways.disk.delete import rm_rf
    from conda.misc import clone_env
    from conda.models.environment import Environment

    from ..constants import RESET_FILE_BASE_PROTECTION, RESET_FILE_INSTALLER
    from ..query import permanent_dependencies
    from ..reset import names_from_explicit, reset

    default_env = DEFAULT_ENV_NAME
    message = BASE_PROTECTION_FROZEN_MESSAGE

    base_prefix = Path(sys.prefix)

    env = Environment.from_prefix(
        str(base_prefix), name="base", platform=context.subdir
    )

    if not context.quiet:
        print(
            f"This will clone the base environment to '{default_env}', reset it, "
            "and mark it as frozen."
        )
        if env.external_packages:
            external_package_count = len(env.external_packages)
            external_package_noun = (
                "package" if external_package_count == 1 else "packages"
            )
            print(
                f"  Warning: Base environment contains {external_package_count} "
                f"external {external_package_noun} that may no longer work in "
                "the reset base environment.\n"
                f"  They are preserved in the cloned '{default_env}' environment."
            )
    confirm("Proceed?")

    # Prefer the installer snapshot for resetting base so that
    # packages recorded in the installer snapshot (e.g. mamba in Miniforge)
    # are preserved.
    installer_snapshot = base_prefix / "conda-meta" / RESET_FILE_INSTALLER
    use_snapshot = installer_snapshot.exists()

    # Check destination environment
    dest_prefix_data = PrefixData.from_name(default_env)

    if dest_prefix_data.is_environment():
        confirm(f"Environment '{default_env}' already exists. Remove and recreate?")
        rm_rf(dest_prefix_data.prefix_path)
    elif dest_prefix_data.exists():
        confirm(f"Directory exists at '{dest_prefix_data.prefix_path}'. Continue?")

    # Save explicit snapshot for potential restore via conda self reset.
    snapshot_file = base_prefix / "conda-meta" / RESET_FILE_BASE_PROTECTION
    try:
        explicit_exporter = context.plugin_manager.get_environment_exporter_by_format(
            "explicit"
        )
        if not context.quiet:
            print(f"Saving snapshot to {snapshot_file}")
        export = explicit_exporter.export
        assert export is not None
        snapshot_file.write_text(export(env))
    except CondaValueError:
        if not context.quiet:
            print(
                "  Skipping snapshot because the base environment cannot be "
                "exported in conda's explicit format."
            )

    if not context.quiet:
        print(f"Cloning the base environment to '{default_env}'...")
        print("Resetting the base environment...")

    # Suppress conda's transaction spinner output when --quiet
    stdout_ctx = redirect_stdout(io.StringIO()) if context.quiet else nullcontext()
    with stdout_ctx:
        clone_env(
            str(base_prefix),
            str(dest_prefix_data.prefix_path),
            verbose=False,
            quiet=True,
        )
        if use_snapshot:
            keep = permanent_dependencies() | names_from_explicit(installer_snapshot)
            reset(uninstallable_packages=keep)
        else:
            reset(uninstallable_packages=permanent_dependencies())

    # Freeze base
    try:
        frozen_path = base_prefix / PREFIX_FROZEN_FILE
        frozen_path.write_text(json.dumps({"message": message}) if message else "")
    except OSError as e:
        raise CondaOSError(f"Could not protect the base environment: {e}") from e

    # Update default activation environment
    if not context.quiet:
        print(f"Setting default environment to '{default_env}'")
    with ConfigurationFile.from_user_condarc() as config:
        config.set_key("default_activation_env", str(dest_prefix_data.prefix_path))

    if not context.quiet:
        print(f"\nDone! To use your packages: conda activate {default_env}")
    return 0
