# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# _compat.py
"""
Anaconda Telemetry - single point of contact with private OpenTelemetry APIs.

Every OpenTelemetry symbol upstream does not guarantee (underscore-prefixed module
or name) is imported here and nowhere else, so a ceiling bump is a one-file audit.
``docs/source/otel-private-api.md`` holds the inventory and the supported range
(opentelemetry-sdk >=1.40.0,<1.44).

A private import that disappears degrades to a no-op with one warning, so it cannot
raise out of a log handler and take down the host application.

Re-exports are annotated ``Any``: each name is bound to unrelated types in the
working and degraded branches.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = [
    "OTEL_PRIVATE_LOGS_AVAILABLE",
    "BatchLogRecordProcessor",
    "ConsoleLogRecordExporter",
    "GaugeInstrument",
    "LoggerProvider",
    "LoggingHandler",
    "LogRecordExporter",
    "get_logger_provider",
    "set_logger_provider",
]


class _UnavailablePrivateAPI:
    """Inert stand-in: constructible and subclassable, every operation a no-op."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        return _UnavailablePrivateAPI()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def __bool__(self) -> bool:
        return False


def _unavailable(*args: Any, **kwargs: Any) -> None:
    return None


set_logger_provider: Any
get_logger_provider: Any
LoggerProvider: Any
LoggingHandler: Any
BatchLogRecordProcessor: Any
ConsoleLogRecordExporter: Any
LogRecordExporter: Any

try:
    import opentelemetry._logs as _api_logs
    import opentelemetry.sdk._logs as _sdk_logs
    import opentelemetry.sdk._logs.export as _sdk_logs_export

    set_logger_provider = _api_logs.set_logger_provider
    get_logger_provider = _api_logs.get_logger_provider

    LoggerProvider = _sdk_logs.LoggerProvider
    LoggingHandler = _sdk_logs.LoggingHandler

    # `LogExporter` is a deprecated alias that warns on subclassing; both names
    # exist across 1.40 - 1.43.
    LogRecordExporter = _sdk_logs_export.LogRecordExporter
    BatchLogRecordProcessor = _sdk_logs_export.BatchLogRecordProcessor
    ConsoleLogRecordExporter = _sdk_logs_export.ConsoleLogRecordExporter

    OTEL_PRIVATE_LOGS_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - only on an unsupported SDK
    logging.getLogger(__package__).warning(
        "Anaconda OpenTelemetry: the installed opentelemetry-sdk does not expose the "
        "private logs API this package requires (%s: %s). Log telemetry is disabled; "
        "metrics and tracing are unaffected. Supported range: >=1.40.0,<1.44.",
        type(_exc).__name__,
        _exc,
    )
    set_logger_provider = _unavailable
    get_logger_provider = _unavailable
    LoggerProvider = _UnavailablePrivateAPI
    LoggingHandler = _UnavailablePrivateAPI
    LogRecordExporter = _UnavailablePrivateAPI
    BatchLogRecordProcessor = _UnavailablePrivateAPI
    ConsoleLogRecordExporter = _UnavailablePrivateAPI
    OTEL_PRIVATE_LOGS_AVAILABLE = False


def _resolve_gauge_instrument() -> Any:
    """Return the synchronous gauge instrument class.

    `opentelemetry.sdk.metrics` still exposes only `_Gauge` as of 1.43. The public
    name is tried first so a promotion needs no code change. Used as a key in the
    aggregation-temporality maps, where a miss silently falls back to the reader
    default -- hence the warning.
    """
    import opentelemetry.sdk.metrics as _sdk_metrics

    for name in ("Gauge", "_Gauge"):
        instrument = getattr(_sdk_metrics, name, None)
        if instrument is not None:
            return instrument
    logging.getLogger(__package__).warning(
        "Anaconda OpenTelemetry: no Gauge instrument found in opentelemetry.sdk.metrics; "
        "gauge aggregation temporality will fall back to the metric reader default."
    )
    return None


GaugeInstrument: Any = _resolve_gauge_instrument()
