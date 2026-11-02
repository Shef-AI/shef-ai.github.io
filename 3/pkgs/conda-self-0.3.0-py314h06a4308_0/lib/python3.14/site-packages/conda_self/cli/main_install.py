from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Install conda plugins in the base environment."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Reinstall each requested package even if it is already installed.",
    )
    parser.add_argument("specs", nargs="+", help="Conda plugins to install")
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context
    from conda.exceptions import CondaValueError, DryRunExit
    from conda.models.match_spec import MatchSpec

    from ..exceptions import NotAPluginError
    from ..install import (
        install_specs_in_protected_env,
        uninstall_specs_in_protected_env,
    )
    from ..validate import conda_plugin_packages, reload_plugin_packages

    specs_to_add = [MatchSpec(spec) for spec in args.specs]

    specs_with_channels = [str(s) for s in specs_to_add if s.get("channel")]
    if specs_with_channels:
        joined = ", ".join(specs_with_channels)
        raise CondaValueError(
            f"Channel-qualified package specs are not supported: {joined}\n"
            "Configure channels via `conda config --add channels <channel>` instead."
        )

    print("Installing packages:", *args.specs)

    returncode = install_specs_in_protected_env(
        args.specs,
        force_reinstall=args.force_reinstall,
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
    )

    if returncode != 0:
        return returncode

    if context.dry_run:
        raise DryRunExit()

    reload_plugin_packages()

    plugin_names = conda_plugin_packages()
    spec_names = [spec.name for spec in specs_to_add]
    invalid_names = [
        name
        for name in spec_names
        if name.lower().replace("_", "-") not in plugin_names
    ]

    if invalid_names:
        uninstall_specs_in_protected_env(invalid_names, yes=True)
        raise NotAPluginError(invalid_names)

    return 0
