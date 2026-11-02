import json
import logging
import subprocess

from anaconda_auth.config import AnacondaAuthConfig
from anaconda_cli_base.console import console

logger = logging.getLogger(__name__)


def is_env_manager_installed(conda_path: str) -> bool:
    """Check if anaconda-env-manager is installed in the base environment."""
    config = AnacondaAuthConfig()
    args = [conda_path, "list", "-n", "base", config.env_manager_package, "--json"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.debug(
            "Failed to check for %s: %s", config.env_manager_package, proc.stderr
        )
        return False

    try:
        packages = json.loads(proc.stdout)
        return any(pkg.get("name") == config.env_manager_package for pkg in packages)
    except (json.JSONDecodeError, TypeError):
        return False


def _tos_plugin_available(conda_path: str) -> bool:
    """Check whether the conda-anaconda-tos plugin is installed in base environment."""
    args = [conda_path, "list", "-n", "base", "conda-anaconda-tos", "--json"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.debug(
            "conda-anaconda-tos probe failed (exit code %d): %s",
            proc.returncode,
            proc.stderr.strip(),
        )
        return False

    try:
        packages = json.loads(proc.stdout)
        return any(pkg.get("name") == "conda-anaconda-tos" for pkg in packages)
    except (json.JSONDecodeError, TypeError):
        return False


def install_env_manager(conda_path: str) -> tuple[bool, str]:
    """Install anaconda-env-manager into the base environment.

    Note:
        ToS acceptance is mostly best-effort: `conda tos interactive` only
        runs when the plugin is available, and transient failures (e.g. a
        network blip) never block the install—`conda install` enforces the
        real ToS gate itself, with a proper `--json` error message. Prompts
        go to stdout via rich (inherited, so interactivity is unaffected);
        stderr is captured and logged instead of printed, so those failures
        don't show up on screen. The one exception is a confirmed rejection:
        we detect it here and fail immediately, rather than printing
        "Installing..." right before `conda install` fails for the same
        reason.
    """
    config = AnacondaAuthConfig()

    console.print("Checking channel Terms of Service...")
    if _tos_plugin_available(conda_path):
        proc = subprocess.run(
            [conda_path, "tos", "interactive"], stderr=subprocess.PIPE, text=True
        )
        if proc.returncode != 0:
            logger.debug(
                "conda tos interactive exited %d: %s", proc.returncode, proc.stderr
            )
            if "CondaToSRejectedError" in proc.stderr:
                detail = proc.stderr.split("CondaToSRejectedError:", 1)[-1].strip()
                return False, detail or "Terms of Service were rejected."

    console.print("Installing anaconda-env-manager...")
    pkg = f"{config.env_manager_channel}::{config.env_manager_package}{config.env_manager_version or ''}"
    args = [conda_path, "install", "--name", "base", pkg, "--yes", "--json"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        error = f"conda install exited with code {proc.returncode}."
        message = None
        # conda writes the --json error payload to stdout, except when it's
        # raised from a pre-command hook (e.g. a rejected ToS), in which case
        # it lands on stderr instead. Try both before falling back to raw text.
        for stream in (proc.stdout, proc.stderr):
            try:
                message = json.loads(stream).get("message")
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if message:
                break
        detail = message or proc.stderr.strip()
        if detail:
            error = f"{error} {detail}"
        logger.debug("Failed to install %s: %s\nstderr: %s", pkg, error, proc.stderr)
        return False, error
    return True, ""


def get_client_token(conda_path: str) -> str | None:
    """Retrieve the anaconda-anon-usage client token via conda run."""
    args = [
        conda_path,
        "run",
        "-n",
        "base",
        "--no-capture-output",
        "python",
        "-c",
        "from anaconda_anon_usage.tokens import client_token; print(client_token())",
    ]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.debug("Failed to get client token: %s", proc.stderr)
        return None
    return proc.stdout.strip() or None


def is_client_registered(conda_path: str) -> bool:
    """Check if the client token is already registered.

    Retrieves the client token from anaconda-anon-usage and checks with the
    read-only client-token-status endpoint.
    """
    token = get_client_token(conda_path)
    if not token:
        return False

    from anaconda_auth.env_logger import check_client_token_status

    return check_client_token_status(token)


def register_org(conda_path: str) -> bool:
    """Register with an organization via conda env-log.

    Delegates org selection and registration to the plugin command.
    The subprocess inherits stdio so the plugin can interact with the user.
    """
    args = [conda_path, "env-log", "register"]
    proc = subprocess.run(args)
    if proc.returncode != 0:
        logger.debug("Failed to register org (exit code %d)", proc.returncode)
        return False
    return True
