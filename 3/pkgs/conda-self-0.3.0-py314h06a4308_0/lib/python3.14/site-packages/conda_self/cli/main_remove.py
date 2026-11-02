from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Remove conda plugins from the base environment."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Bypass conda-self's check for permanent packages and their "
            "dependencies. Conda still applies its own transaction checks. "
            "Confirmation is still required unless --yes is passed."
        ),
    )
    parser.add_argument("specs", nargs="+", help="Conda plugins to remove")
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context
    from conda.reporters import confirm_yn

    from ..exceptions import PluginRemoveError
    from ..install import uninstall_specs_in_protected_env
    from ..query import permanent_dependencies

    uninstallable_packages = permanent_dependencies(add_plugins=False)
    protected_specs = [spec for spec in args.specs if spec in uninstallable_packages]

    if protected_specs and not args.force:
        raise PluginRemoveError(protected_specs)

    if protected_specs:
        print(
            "Warning: --force bypassed conda-self's check for the following packages:",
            ", ".join(protected_specs),
            file=sys.stderr,
        )

    print("Removing packages:", *args.specs)

    confirm_yn(
        "Proceed with removing packages?[y/n]:\n",
        default="no",
        dry_run=context.dry_run,
    )

    uninstall_specs_in_protected_env(args.specs, json=context.json, yes=True)
    return 0
