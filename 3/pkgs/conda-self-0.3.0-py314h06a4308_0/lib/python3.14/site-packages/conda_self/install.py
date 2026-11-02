import sys
from subprocess import run

from conda.base.context import context


def install_specs_in_protected_env(
    specs: list[str],
    force_reinstall: bool = False,
    update_dependencies: bool = False,
    update_all: bool = False,
    dry_run: bool = False,
    json: bool = False,
    yes: bool = False,
    quiet: bool = False,
) -> int:
    """Install or update specs into the protected base env via subprocess."""
    if update_all:
        update_flag = "--all"
    elif update_dependencies:
        update_flag = "--update-deps"
    else:
        update_flag = "--update-specs"
    process = run(
        [
            sys.executable,
            "-m",
            "conda",
            "install",
            f"--prefix={sys.prefix}",
            *(
                ("--override-frozen",)
                if hasattr(context, "protect_frozen_envs")
                else ()
            ),
            *(("--force-reinstall",) if force_reinstall else ()),
            *(("--dry-run",) if dry_run else ()),
            *(("--json",) if json else ()),
            *(("--yes",) if yes else ()),
            *(("--quiet",) if quiet else ()),
            update_flag,
            *specs,
        ]
    )
    return process.returncode


def uninstall_specs_in_protected_env(
    specs: list[str],
    json: bool = False,
    yes: bool = True,
) -> int:
    cmd = [
        sys.executable,
        "-m",
        "conda",
        "remove",
        f"--prefix={sys.prefix}",
        *(("--override-frozen",) if hasattr(context, "protect_frozen_envs") else ()),
        *(("--json",) if json else ()),
        *(("--yes",) if yes else ()),
        *specs,
    ]
    process = run(cmd)
    return process.returncode
