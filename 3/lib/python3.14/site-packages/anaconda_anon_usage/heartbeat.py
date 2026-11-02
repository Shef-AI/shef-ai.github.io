"""
This module implements a heartbeat function that sends a simple
HEAD request to an upstream repository. It can be configured to
trigger upon environment activation, but it is off by default.
The intended use case is for organizations to enable it through
system configuration for better usage tracking.
"""

import argparse
import os
import sys
import time
from threading import Thread
from urllib.parse import urljoin

from conda.base.context import Context, context, locate_prefix_by_name
from conda.gateways.connection.session import get_session
from conda.models.channel import Channel
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from . import utils

VERBOSE = False
STANDALONE = False

CLD_REPO = "https://repo.anaconda.cloud/"
ORG_REPO = "https://conda.anaconda.org/"
COM_REPO = "https://repo.anaconda.com/pkgs/"
REPOS = (CLD_REPO, COM_REPO, ORG_REPO)
HEARTBEAT_PATH = "noarch/activate-0.0.0-0.conda"

# How long to attempt the connection. When a connection to our
# repository is blocked or slow, a long timeout would lead to
# a slow activation and a poor user experience. This is a total
# timeout value, inclusive of all retries.
TIMEOUT = 0.75  # seconds
ATTEMPTS = 3


def _print(msg, *args, error=False):
    global VERBOSE
    global STANDALONE
    if not (VERBOSE or utils.DEBUG or error):
        return
    # It is very important that these messages are printed to stderr
    # when called from within the activate script. Otherwise they
    # will insert themselves into the activation command set
    ofile = sys.stdout if STANDALONE and not (error or utils.DEBUG) else sys.stderr
    print(msg % args, file=ofile)


def _ping(session, url, timeout):
    try:
        # A short timeout is necessary here so that the activation
        # is not unduly delayed by a blocked internet connection
        start_time = time.perf_counter()
        response = session.head(url, proxies=session.proxies, timeout=timeout)
        delta = time.perf_counter() - start_time
        _print(
            "Success after %.3fs; code (expect 404): %d", delta, response.status_code
        )
    except Exception as exc:
        delta = time.perf_counter() - start_time

        # Check if this is an expected network-related exception
        # Requests exceptions cover most cases, urllib3 for lower-level errors,
        # and standard library for fallback
        if isinstance(exc, (RequestException, HTTPError, OSError, TimeoutError)):
            _print("Heartbeat failed after %.3fs: %s", delta, type(exc).__name__)
        else:
            # Truly unexpected error - log even in non-debug mode
            _print("Unexpected heartbeat error after %.3fs: %s", delta, exc, error=True)


def attempt_heartbeat(prefix=None, dry_run=False, channel=None, path=None):
    if not hasattr(context, "_aau_initialized"):
        from . import patch

        patch.main()

    if channel and "/" in channel:
        url = channel
    else:
        # Silences the defaults deprecation error
        if not context._channels:
            context._channels = ["defaults"]
        urls = [u for c in context.channels for u in Channel(c).urls()]
        urls.extend(u.rstrip("/") for u in context.channel_alias.urls())
        for base in REPOS:
            if any(u.startswith(base) for u in urls):
                break
        else:
            _print("No valid heartbeat channel")
            return
        url = urljoin(base, channel or "main") + "/"
    if path is None:
        path = HEARTBEAT_PATH
    url = urljoin(url, path)

    _print("Heartbeat url: %s", url)
    if prefix:
        Context.checked_prefix = prefix
        _print("Prefix: %s", prefix)
    _print("User agent: %s", context.user_agent)

    if dry_run:
        _print("Dry run selected, not sending heartbeat.")
        return

    # Build and configure the session object
    timeout = TIMEOUT / ATTEMPTS
    context.remote_max_retries = ATTEMPTS - 1
    # No backoff between attempts
    context.remote_backoff_factor = 0
    session = get_session(url)

    # Run in the background so we can proceed with the rest of the
    # activation tasks while the request fires. The process will wait
    # to terminate until the thread is complete.
    t = Thread(target=_ping, args=(session, url, timeout), daemon=False)
    t.start()
    if STANDALONE:
        t.join()


def main():
    global VERBOSE
    global STANDALONE
    STANDALONE = True
    VERBOSE = "--quiet" not in sys.argv and "-q" not in sys.argv

    line = "-----------------------------"
    _print(line)
    _print("anaconda-anon-usage heartbeat")
    _print(line)

    def environment_path(s):
        assert os.path.isdir(s)
        return s

    def environment_name(s):
        return locate_prefix_by_name(s)

    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "-n",
        "--name",
        type=environment_name,
        default=None,
        help="Environment name; defaults to the current environment.",
    )
    g.add_argument(
        "-p",
        "--prefix",
        type=environment_path,
        default=None,
        help="Environment prefix; defaults to the current environment.",
    )
    p.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Do not send the heartbeat; just show the steps.",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress console logs.")
    p.add_argument(
        "--channel",
        default=None,
        help="(advanced) The full URL to a custom repository channel. By default, an "
        "Anaconda-hosted channel listed in the user's channel configuration is used.",
    )
    p.add_argument(
        "--path",
        default=None,
        help="(advanced) A custom path to append to the channel URL.",
    )

    try:
        args = p.parse_args()
        attempt_heartbeat(
            prefix=args.prefix or args.name,
            dry_run=args.dry_run,
            channel=args.channel,
            path=args.path,
        )
    finally:
        _print(line)


if __name__ == "__main__":
    main()
