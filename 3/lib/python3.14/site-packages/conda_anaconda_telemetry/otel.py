# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Configuration and control class for Anaconda OpenTelemetry."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import anaconda_opentelemetry.signals as sig
import requests.utils
from anaconda_opentelemetry.attributes import ResourceAttributes
from anaconda_opentelemetry.config import Configuration
from conda.base.context import context
from conda.exceptions import InvalidMatchSpec
from conda.models.match_spec import MatchSpec

from conda_anaconda_telemetry import APP_NAME, APP_VERSION
from conda_anaconda_telemetry.resource_attributes import (
    get_conda_attributes,
    get_installer_attributes,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from conda.plugins.types import CondaExceptionEvent

logger = logging.getLogger(__name__)

#: Schema version for the created signal,
#: bump manually whenever this contents/shape change.
SIGNAL_VERSION = "1"


#: These two limits below mirror what is in the HTTP-backend.
#: Item limit for list-valued event attributes.
LIST_ITEM_LIMIT = 50
#: UTF-8 byte limit for list-valued event attributes.
LIST_BYTE_LIMIT = 500

#: Channel names allowed in the install.channels payload; anything else is
#: reported as OTHER_CHANNEL_LABEL so a channel URL or internal name can't
#: reach the payload.
KNOWN_INSTALL_CHANNELS = frozenset({"defaults", "main", "main-x", "conda-forge"})
OTHER_CHANNEL_LABEL = "other"

#: Hosts accepted for a local collector set with ATEL_DEFAULT_ENDPOINT.
_LOCAL_COLLECTOR_HOSTS = ("localhost", "127.0.0.1")

# From running scripts/benchmark_timing.sh the slowest observed
# flush (~2.3-2.9s outlier) is covered by the 3.0s timeout
# without excessive stalling
_SHUTDOWN_TIMEOUT_SECONDS = 3.0


def _service_version(version: str) -> str:
    """Format the version to be accepted by OTel SDK.

    Drop the dev and local (``+...``) parts, otherwise a ValueError is raised.
    """
    return version.partition(".dev")[0].partition("+")[0]


@contextmanager
def _ignore_otel_environment() -> Iterator[None]:
    """Ignore native OTel settings while initializing or emitting an event."""
    # tuple() makes a copy of the names. Without it, removing a variable
    # inside this loop raises "dictionary changed size during iteration".
    saved_env = {
        var: os.environ.pop(var, None)
        for var in tuple(os.environ)
        if var.startswith("OTEL_")
    }
    try:
        yield
    finally:
        for var, value in saved_env.items():
            if value is not None:
                os.environ[var] = value


class Environment(Enum):
    """Environment enum."""

    DEFAULT = ""
    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class AnacondaTelemetry:
    """Anaconda Telemetry configuration and control class."""

    service_name: str = APP_NAME
    service_version: str = _service_version(APP_VERSION)
    platform: str = "conda"
    environment: Environment = field(
        init=False,
        default_factory=lambda: Environment(
            os.getenv("ATEL_ENVIRONMENT", "production")
        ),
    )
    default_endpoint: str = field(init=False)

    def __post_init__(self) -> None:
        """Use the production endpoint unless a local collector is selected.

        ATEL_ENVIRONMENT labels events without selecting a destination.
        ATEL_DEFAULT_ENDPOINT can select a local HTTP collector for testing.
        Other endpoint overrides are ignored.
        """
        self.default_endpoint = "https://public.telemetry.anaconda.com/v1/logs"

        default_endpoint = os.getenv("ATEL_DEFAULT_ENDPOINT")
        if default_endpoint is not None:
            parsed_endpoint = urlparse(default_endpoint)
            if (
                parsed_endpoint.scheme == "http"
                and parsed_endpoint.hostname in _LOCAL_COLLECTOR_HOSTS
            ):
                self.default_endpoint = default_endpoint

    def _make_config(self) -> Configuration:
        config = Configuration(
            default_endpoint=self.default_endpoint,
            ignore_environment_variables=True,
        )
        config.set_disable_session_id(True)
        # Use conda's own proxy config instead of ATEL_PROXY_URL.
        config.set_proxy_url(
            requests.utils.select_proxy(self.default_endpoint, context.proxy_servers)
        )
        # Never probe connectivity before sending an event: skip this for every
        # endpoint, not just localhost, so a slow/unreachable network can't add
        # latency to a conda command that's just trying to report an error.
        config.set_skip_internet_check(True)
        # Manage shutdown ourselves (see shutdown() below) with a fixed timeout,
        # instead of letting the SDK register its own unbounded atexit handler.
        config.set_shutdown_on_exit(False)
        if urlparse(self.default_endpoint).hostname in _LOCAL_COLLECTOR_HOSTS:
            # Local collectors still export over real OTLP, not the console.
            config.set_console_exporter(False)
        return config

    def _make_attributes(self) -> ResourceAttributes:
        attributes = ResourceAttributes(
            self.service_name,
            self.service_version,
            anon_usage=True,
            exclude_auto_collect=["hostname"],
        )
        attributes.set_attributes(
            platform=self.platform,
            environment=self.environment.value,
        )
        # Apply setattr() directly to ensure these are top-level attributes.
        for key, value in {
            **get_installer_attributes(),
            **get_conda_attributes(),
        }.items():
            setattr(attributes, key, value)
        return attributes

    def initialize(self) -> None:
        """Initialize telemetry."""
        with _ignore_otel_environment():
            sig.initialize_telemetry(
                config=self._make_config(),
                attributes=self._make_attributes(),
                signal_types=["logging"],
            )

    def send_event(
        self, event_name: str, body: str, attributes: dict[str, Any] | None = None
    ) -> None:
        """Send a telemetry event and flush it within a fixed time budget.

        This only queues the event; it is not actually sent until shutdown()
        flushes it. Since _make_config() turns off the SDK's automatic
        shutdown, that flush is called here so callers can't forget it.
        """
        if attributes is None:
            attributes = {}

        logger.info("Sending a signal with event log data to the telemetry collector.")

        try:
            # OTel reads attribute limits again when constructing each log record.
            with _ignore_otel_environment():
                result = sig.send_event(
                    event_name=event_name,
                    body=body,
                    attributes=attributes,
                )

            if result is True:
                logger.info("Event log queued.")
            else:
                logger.debug("Event log failed to send.")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Flush pending telemetry within a fixed time budget.

        sig.shutdown_telemetry() implements this same timeout pattern but is
        one-shot per process and send_event() calls this after every
        event. Use the repeatable sig.flush_telemetry() instead. Run it on a
        daemon thread and bound the caller's wait with join() because the flush
        itself could be unbounded since a flush that exceeds the timeout keeps
        running in the background until process exit.
        """
        flush_thread = threading.Thread(target=sig.flush_telemetry, daemon=True)
        flush_thread.start()
        flush_thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)


def package_names(specs: list[Any]) -> list[str] | None:
    """Return exact names, or None when the request cannot be represented."""
    names = set()
    for value in specs:
        try:
            spec = MatchSpec(value)
        except InvalidMatchSpec:
            return None

        name = spec.get_exact_value("name")
        if (
            spec.get_raw_value("url")
            or not name
            or not re.fullmatch(r"[a-z0-9_.-]+", name)
        ):
            return None
        names.add(name)

    return sorted(names)


def _truncate(
    items: list[Any],
    item_limit: int = LIST_ITEM_LIMIT,
    byte_limit: int = LIST_BYTE_LIMIT,
) -> tuple[list[Any], bool]:
    """Truncate a list to an item count and a serialized UTF-8 byte limit.

    Returns the possibly-shortened list and whether anything was dropped.
    """
    truncated = len(items) > item_limit
    kept: list[Any] = []
    for item in items[:item_limit]:
        candidate = [*kept, item]
        if len(json.dumps(candidate).encode("utf-8")) > byte_limit:
            truncated = True
            break
        kept = candidate
    return kept, truncated


def _get_command_attributes(
    *, command: str, channels: list[str], requested_names: list[str]
) -> tuple[dict[str, Any], bool]:
    """Build fields shared by install/create error and success events."""
    safe_channels, channels_truncated = _truncate(
        [
            channel if channel in KNOWN_INSTALL_CHANNELS else OTHER_CHANNEL_LABEL
            for channel in channels
        ]
    )
    packages, packages_truncated = _truncate(requested_names)
    return (
        {
            "command": command,
            "event.schema_version": SIGNAL_VERSION,
            "install.channels": safe_channels,
            "install.channel_priority": str(context.channel_priority),
            "requested.packages": packages,
        },
        channels_truncated or packages_truncated,
    )


def get_install_attributes(
    event: CondaExceptionEvent,
    *,
    command: str,
    requested_names: list[str],
) -> dict[str, Any] | None:
    """Build the event from captured package names and the failure snapshot."""
    missing_names = package_names(list(event.exc_value.packages))
    if missing_names is None:
        logger.debug("Skipping telemetry because package names could not be read.")
        return None

    attributes, truncated = _get_command_attributes(
        command=command,
        channels=list(event.channels or ()),
        requested_names=requested_names,
    )
    missing_specs, missing_specs_truncated = _truncate(missing_names)

    return {
        **attributes,
        "exception.name": event.exc_type.__name__,
        "exception.missing_specs": missing_specs,
        "truncated": truncated or missing_specs_truncated,
    }


def get_success_attributes(
    *,
    command: str,
    channels: list[str],
    requested_names: list[str],
    resolved_packages: list[str],
) -> dict[str, Any]:
    """Build attributes for an install/create success signal."""
    attributes, truncated = _get_command_attributes(
        command=command, channels=channels, requested_names=requested_names
    )
    resolved, resolved_truncated = _truncate(resolved_packages)

    return {
        **attributes,
        "resolved.packages": resolved,
        "truncated": truncated or resolved_truncated,
    }
