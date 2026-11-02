from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Update conda, one conda plugin, or all packages in the base environment."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help=(
            "Uninstall and reinstall each requested package, even if it is "
            "already installed."
        ),
    )
    update_group = parser.add_mutually_exclusive_group()
    update_group.add_argument(
        "--plugin",
        help="Name of a conda plugin to update",
    )
    update_group.add_argument(
        "--all",
        action="store_true",
        help="Update all installed packages in the base environment.",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context
    from conda.core.prefix_data import PrefixData
    from conda.exceptions import PackageNotInstalledError

    from ..install import install_specs_in_protected_env
    from ..validate import conda_plugin_packages, validate_plugin_is_installed

    if args.plugin:
        validate_plugin_is_installed(args.plugin)
        package_names = [args.plugin]
    elif args.all:
        package_names = ["conda", *conda_plugin_packages()]
    else:
        package_names = ["conda"]

    prefix_data = PrefixData(context.root_prefix)

    info_parts = []
    for name in package_names:
        installed = prefix_data.get(name)
        if not installed:
            raise PackageNotInstalledError(context.root_prefix, name)
        info_parts.append(f"{name} (installed: {installed.version})")

    quiet = context.quiet or bool(args.quiet)
    if not context.json and not quiet:
        if args.all:
            print("Updating all installed packages...")
        else:
            print(f"Updating {', '.join(info_parts)}...")

    return install_specs_in_protected_env(
        specs=package_names,
        force_reinstall=args.force_reinstall,
        update_dependencies=not args.all,
        update_all=args.all,
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
        quiet=quiet,
    )
