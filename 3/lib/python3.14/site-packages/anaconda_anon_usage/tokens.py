# This module provides functions for reading and writing the
# anonymous token set. It has been designed to rely only on the
# Python standard library. In particular, hard dependencies on
# conda must be avoided so that this package can be used in
# child environments.

import base64
import datetime as dt
import json
import re
import sys
import uuid
from collections import namedtuple
from os import environ
from os.path import basename, dirname, expanduser, isfile, join

from . import __version__
from .utils import _debug, _random_token, _read_file, _saved_token, cached

Tokens = namedtuple(
    "Tokens",
    (
        "version",
        "client",
        "session",
        "environment",
        "anaconda_cloud",
        "installer",
        "organization",
        "machine",
    ),
)
CONFIG_DIR = expanduser("~/.conda")
ANACONDA_DIR = expanduser("~/.anaconda")
ORG_TOKEN_NAME = "org_token"
INSTALLER_TOKEN_NAME = "installer_token"
MACHINE_TOKEN_NAME = "machine_token"

# System tokens may consist of only letters, numbers,
# underscores, and dashes, with no more than 36 characters.
VALID_TOKEN_RE = r"^(?:[A-Za-z0-9]|_|-){1,36}$"


@cached
def version_token():
    """
    Returns the version token, which is just the
    version string itself.
    """
    return __version__


def _conda_root():
    """Resolve the conda root/base environment prefix.

    Tries these sources in order, returning the first that succeeds:
    1. $CONDA_ROOT — set by activation scripts or sys.prefix
    2. $CONDA_EXE — grandparent of the conda executable path
    3. $CONDA_PYTHON_EXE — platform-dependent extraction
       - Unix: .../bin/python -> grandparent
       - Windows: .../python.exe -> parent
    4. Walk $PATH for a condabin entry -> its parent directory
    """
    # 1. CONDA_ROOT — direct
    conda_root = environ.get("CONDA_ROOT", "")
    if conda_root:
        return conda_root

    # 2. CONDA_EXE — grandparent (strip filename + bin/Scripts)
    conda_exe = environ.get("CONDA_EXE", "")
    if conda_exe:
        return dirname(dirname(conda_exe))

    # 3. CONDA_PYTHON_EXE — platform-dependent
    conda_python_exe = environ.get("CONDA_PYTHON_EXE", "")
    if conda_python_exe:
        if sys.platform == "win32":
            # Windows: .../python.exe -> parent
            return dirname(conda_python_exe)
        else:
            # Unix: .../bin/python -> grandparent
            return dirname(dirname(conda_python_exe))

    # 4. Walk PATH for a condabin directory
    path_var = environ.get("PATH", "")
    sep = ";" if sys.platform == "win32" else ":"
    for entry in path_var.split(sep):
        if entry and basename(entry) == "condabin":
            return dirname(entry)

    return None


@cached
def _search_path():
    """
    Returns the search path for system tokens.

    Deterministic path construction — does not import conda.
    Identical logic in the Rust anaconda-anon-usage crate.
    """
    # Test-only: override system paths for isolation (not a public API)
    test_root = environ.get("ANACONDA_ANON_USAGE_TEST_SYSTEM_ROOT")
    if test_root:
        dirs = [test_root]
    elif sys.platform == "win32":
        dirs = ["C:/ProgramData/conda"]
    else:
        dirs = ["/etc/conda", "/var/lib/conda"]

    conda_root = _conda_root()
    if conda_root:
        dirs.append(conda_root)

    xdg = environ.get("XDG_CONFIG_HOME")
    if xdg:
        dirs.append(xdg + "/conda")

    home = expanduser("~")
    # If $HOME is unset, expanduser returns "~" verbatim. Skip home-based
    # entries in that case; appending literal "~/.conda" would point at a
    # relative path from the cwd, not an unintended system location.
    if home != "~":
        dirs.append(home + "/.config/conda")
        dirs.append(home + "/.conda")

    conda_prefix = environ.get("CONDA_PREFIX")
    if conda_prefix and conda_prefix != conda_root:
        dirs.append(conda_prefix)

    return dirs


def _system_tokens(fname, what, with_source=False):
    """
    Returns an organization or machine token installed somewhere
    in the conda path. Unlike most tokens, these will typically
    be installed by system administrators, often by mobile device
    management software. There can also be multiple tokens present
    along the path, in which case we combine them
    """
    tokens = []
    env_name = "ANACONDA_ANON_USAGE_" + fname.upper()
    t_token = environ.get(env_name)
    if t_token:
        _debug("Found %s token in environment: %s", what, t_token)
        tokens.append((t_token, "$" + env_name))
    for path in _search_path():
        for pfx in ("", "."):
            fpath = join(path, pfx + fname)
            if isfile(fpath):
                t_token = _read_file(fpath, what + " token", single_line=True)
                tokens.append((t_token, fpath))
    # Deduplicate by token value while preserving order
    seen = set()
    tokens = [(t, s) for t, s in tokens if t and t not in seen and not seen.add(t)]
    if not tokens:
        _debug("No %s tokens found", what)
    # Make sure the tokens we emit have only valid characters, so any
    # server-side token parsing is not frustrated.
    valid = [(t, s) for t, s in tokens if re.match(VALID_TOKEN_RE, t)]
    if len(valid) < len(tokens):
        invalid = ", ".join(t for t, _ in tokens if not re.match(VALID_TOKEN_RE, t))
        _debug("One or more invalid %s tokens discarded: %s", what, invalid)
    if with_source:
        return valid
    return [t for t, _ in valid]


@cached
def installer_tokens():
    """
    Returns the list of installer tokens.
    """
    return _system_tokens(INSTALLER_TOKEN_NAME, "installer")


@cached
def organization_tokens():
    """
    Returns the list of organization tokens.
    """
    return _system_tokens(ORG_TOKEN_NAME, "organization")


@cached
def machine_tokens():
    """
    Returns the list of machine tokens.
    """
    return _system_tokens(MACHINE_TOKEN_NAME, "machine")


@cached
def client_token():
    """
    Returns the client token. If a token has not yet
    been generated, an attempt is made to do so. If
    that fails, an empty string is returned.
    """
    fpath = join(CONFIG_DIR, "aau_token")
    return _saved_token(fpath, "client", node_tie=True)


@cached
def session_token():
    """
    Returns the session token, generated randomly for each
    execution of the process.
    """
    return _random_token("session")


@cached
def environment_token(prefix=None):
    """
    Returns the environment token for the given prefix, or
    sys.prefix if one is not supplied. If a token has not
    yet been generated, an attempt is made to do so. If that
    fails, an empty string is returned.
    """
    if prefix is None:
        prefix = sys.prefix
    # An empty prefix would resolve `join("", "etc", "aau_token")` to the
    # relative path `etc/aau_token`, which could accidentally target
    # wherever the process happens to be running. Skip instead.
    if not prefix:
        return ""
    fpath = join(prefix, "etc", "aau_token")
    return _saved_token(fpath, "environment", prefix)


def _jwt_to_token(s):
    """Unpacks an Anaconda auth token and returns the encoded user ID for
    potential inclusion in the user agent, along with its expiration.

    The Anaconda API key takes the form of a standard OAuth2 access token,
    with the additional requirement that the "sub" field is a UUID string.
    This code perorms a basic set of integrity checks to confirm that this
    is the case. If the checks pass, the function returns an encoded form
    of "sub" as well as the "exp" value to enable sorting by expiration.
    If the checks fail, the function returns (None, 0).

    The signature is not fully validated as part of the check; only that it
    is a base64-encoded value. Validation is left to anaconda-auth.

    Returns:
      token: the token if valid; None otherwise
      exp: the expiration time
    """
    if not s:
        return
    try:
        # The JWT should have three parts separated by periods
        parts = s.split(".")
        assert len(parts) == 3 and all(parts), "3 parts expected"
        # Each part should be base64 encoded
        parts = list(map(lambda x: base64.urlsafe_b64decode(x + "==="), parts))
        # The header and payload should be json dictionaries
        parts = list(map(json.loads, parts[:2]))
        assert isinstance(parts[0], dict), "Invalid header"
        assert parts[0].get("typ") == "JWT", "Invalid header"
        assert isinstance(parts[1], dict), "Invalid payload"
        # The payload should have a positive integer expiration
        exp = parts[1].get("exp")
        assert isinstance(exp, int) and exp > 0, "Invalid expiration"
        now = dt.datetime.now(tz=dt.timezone.utc).timestamp()
        if exp < now:
            _debug("API key expired %ds ago", int(now - exp))
            return
        # The subscriber should be a non-empty UUID string
        sub = parts[1].get("sub")
        assert sub, "Invalid subscriber"
        # This is an Anaconda requirement, not a JWT requirement
        sub = uuid.UUID(sub).bytes
        token = base64.urlsafe_b64encode(sub).decode("ascii").strip("=")
        return token
    except Exception as exc:
        _debug("Unexpected %s parsing API key: %s", type(exc), exc)


@cached
def anaconda_auth_token():
    """Returns the base64-encoded uid corresponding to the logged
    in Anaconda Cloud user, if one is present.
    Returns:
        str: Base64-encoded token, or None if no valid token found.
    """
    try:
        from anaconda_auth.token import TokenInfo, TokenNotFoundError

        _debug("Module anaconda_auth loaded")
        tinfo = TokenInfo.load(domain="anaconda.com")
        if tinfo.api_key:
            token = _jwt_to_token(tinfo.api_key)
            _debug("Retrieved Anaconda auth token: %s", token)
            return token
    except ImportError:
        _debug("Module anaconda_auth not available")
    except TokenNotFoundError:
        pass
    except Exception as exc:
        _debug("Unexpected error retrieving token using anaconda_auth: %s", exc)
    _debug("No Anaconda API token found")


@cached
def all_tokens(prefix=None):
    """
    Returns the token set, in the form of a Tokens namedtuple.
    Fields: version, client, session, environment
    """
    return Tokens(
        version_token(),
        client_token(),
        session_token(),
        environment_token(prefix),
        anaconda_auth_token(),
        installer_tokens(),
        organization_tokens(),
        machine_tokens(),
    )


@cached
def token_string(prefix=None, enabled=True):
    """
    Returns the token set, formatted into the string that is
    appended to the conda user agent.
    """
    parts = ["aau/" + __version__]
    if enabled:
        values = all_tokens(prefix)
        if values.client:
            parts.append("c/" + values.client)
        if values.session:
            parts.append("s/" + values.session)
        if values.environment:
            parts.append("e/" + values.environment)
        if values.anaconda_cloud:
            parts.append("a/" + values.anaconda_cloud)
        # System tokens can potentially be multi-valued, and this
        # is rendered in the user agent string as multiple instances
        # separated by spaces. This was chosen to facilitate easier
        # filtering & search
        if values.installer:
            parts.extend("i/" + t for t in values.installer)
        if values.organization:
            parts.extend("o/" + t for t in values.organization)
        if values.machine:
            parts.extend("m/" + t for t in values.machine)
    else:
        _debug("anaconda_anon_usage disabled by config")
    result = " ".join(parts)
    _debug("Full aau token string: %s", result)
    return result


if __name__ == "__main__":
    from .main import main

    main()
