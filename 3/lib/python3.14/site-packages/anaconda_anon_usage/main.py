"""Command-line entry point for the ``anaconda-anon-usage`` executable."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .tokens import (
    INSTALLER_TOKEN_NAME,
    MACHINE_TOKEN_NAME,
    ORG_TOKEN_NAME,
    _search_path,
    _system_tokens,
    all_tokens,
    token_string,
)
from .utils import _debug, _random_token

_PLATFORMS = ("windows", "darwin", "linux")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="anaconda-anon-usage",
        description=f"anaconda-anon-usage {__version__} (Python package)",
        epilog=(
            "Example:\n"
            "  anaconda-anon-usage --attribution installer.exe"
            " --prefix /opt/conda --platform windows"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", action="count", default=0, help="Increase verbosity"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Print the package version",
    )
    parser.add_argument(
        "--detail", action="store_true", help="Print per-token provenance"
    )
    parser.add_argument(
        "--prefix", metavar="PATH", help="Use PATH as the environment prefix"
    )
    parser.add_argument(
        "--jwt", metavar="TOKEN", help="Use TOKEN as the Anaconda auth JWT"
    )
    parser.add_argument(
        "--no-keyring", action="store_true", help="Disable keyring lookups"
    )
    parser.add_argument(
        "--paths", action="store_true", help="Print the system token search path"
    )
    parser.add_argument(
        "--random", action="store_true", help="Generate and print a random token"
    )

    attr = parser.add_argument_group("attribution (installer token extraction)")
    attr.add_argument(
        "--attribution", metavar="FILE", help="Extract installer token from FILE"
    )
    attr.add_argument(
        "--platform",
        choices=_PLATFORMS,
        help="Override platform (windows/darwin/linux)",
    )
    return parser


def _run_attribution(attribution, prefix, platform_override):
    if prefix is None:
        print("--attribution requires --prefix", file=sys.stderr)
        sys.exit(1)
    from .attribution import save_installer_attribution

    installer_file = Path(attribution)
    if not installer_file.is_file():
        print(f"Error: {installer_file} does not exist.", file=sys.stderr)
        sys.exit(1)
    token_file = Path(prefix) / ("." + INSTALLER_TOKEN_NAME)
    try:
        saved = save_installer_attribution(
            installer_file, token_file, platform_override
        )
        if saved:
            _debug("Installer token saved to %s", token_file)
        else:
            _debug("No attribution data found in installer.")
    except RuntimeError as e:
        _debug("Warning: %s", e)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _print_detail(prefix):
    tokens = all_tokens(prefix)
    field_info = [
        ("c", "client", tokens.client, "~/.conda/aau_token"),
        ("s", "session", tokens.session, "random (per-process)"),
        (
            "e",
            "environment",
            tokens.environment,
            f"{prefix or '$CONDA_PREFIX'}/etc/aau_token",
        ),
        ("a", "anaconda", tokens.anaconda_cloud, "jwt (sub claim)"),
    ]
    for pfx, label, value, source in field_info:
        if value:
            print(f"  {pfx}/{value} ({label}) <- {source}")
    for pfx, label, fname in [
        ("i", "installer", INSTALLER_TOKEN_NAME),
        ("o", "organization", ORG_TOKEN_NAME),
        ("m", "machine", MACHINE_TOKEN_NAME),
    ]:
        for v, source in _system_tokens(fname, label, with_source=True):
            print(f"  {pfx}/{v} ({label}) <- {source}")


def main():
    """CLI for testing anaconda-anon-usage token generation."""
    args = _build_parser().parse_args()

    if args.verbose:
        from . import utils

        utils.DEBUG = True

    if args.paths:
        for p in _search_path():
            print(p)
        return
    if args.random:
        print(_random_token())
        return

    if args.attribution:
        _run_attribution(args.attribution, args.prefix, args.platform)
        return

    if args.jwt:
        os.environ["ANACONDA_AUTH_API_KEY"] = args.jwt
    elif args.no_keyring:
        os.environ["ANACONDA_DOMAIN"] = "__disabled__"

    print(token_string(args.prefix))
    if args.detail:
        _print_detail(args.prefix)


if __name__ == "__main__":
    main()
