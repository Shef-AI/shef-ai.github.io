# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import threading

import pytest


def pytest_unconfigure(config):
    """Hard-exit if OTel daemon threads linger, to avoid a ~30s interpreter hang.

    The OTel SDK registers atexit handlers for each BatchSpanProcessor /
    BatchLogRecordProcessor / PeriodicExportingMetricReader created during the
    run. At interpreter shutdown each tries to flush to a collector that isn't
    there, and every one blocks for its full export timeout.

    This runs in pytest_unconfigure -- after the terminal summary and after
    pytest-cov has written its reports -- so os._exit() cannot truncate output.
    """
    if not any(t.daemon and 'Otel' in t.name for t in threading.enumerate()):
        return

    exitstatus = getattr(config, '_otel_exitstatus', 0)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitstatus)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """Record the real exit status for pytest_unconfigure to hand to os._exit."""
    session.config._otel_exitstatus = int(exitstatus)
