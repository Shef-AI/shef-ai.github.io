# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

"""Tests for shutdown_on_exit control, flush_telemetry, and shutdown_telemetry.

These tests are intentionally self-contained: they do not contact a real OTel
collector. Network is avoided via Configuration.set_skip_internet_check(True)
and Configuration.set_console_exporter(True), and the bound/idempotency tests
monkeypatch the in-module flush_telemetry to avoid touching OTel globals at
all.
"""

import sys
sys.path.append("./")

import time
from unittest.mock import patch, MagicMock

import pytest

from opentelemetry import _logs
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

import anaconda_opentelemetry.signals as sig
from anaconda_opentelemetry.attributes import ResourceAttributes
from anaconda_opentelemetry.config import Configuration
from anaconda_opentelemetry.logging import _AnacondaLogger
from anaconda_opentelemetry.metrics import _AnacondaMetrics
from anaconda_opentelemetry.signals import initialize_telemetry
from anaconda_opentelemetry.tracing import _AnacondaTrace


# ---------------------------------------------------------------------------
# Fixture: reset module-level singleton state between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """Reset module-level singleton state between tests."""
    # Defensive: undo any prior test's monkeypatch of these references
    sig._AnacondaTrace = _AnacondaTrace
    sig._AnacondaMetrics = _AnacondaMetrics
    sig._AnacondaLogger = _AnacondaLogger

    # Save original state
    orig_init = sig.__ANACONDA_TELEMETRY_INITIALIZED
    orig_shutdown = sig._SHUTDOWN_DONE
    orig_logger = _AnacondaLogger._instance
    orig_metrics = _AnacondaMetrics._instance
    orig_trace = _AnacondaTrace._instance

    # Reset to a clean baseline. __ANACONDA_TELEMETRY_INITIALIZED is a module-level
    # global (not a class attribute), so Python name mangling does not apply here.
    sig.__ANACONDA_TELEMETRY_INITIALIZED = False
    sig._SHUTDOWN_DONE = False
    _AnacondaLogger._instance = None
    _AnacondaMetrics._instance = None
    _AnacondaTrace._instance = None

    yield

    # Restore
    sig.__ANACONDA_TELEMETRY_INITIALIZED = orig_init
    sig._SHUTDOWN_DONE = orig_shutdown
    _AnacondaLogger._instance = orig_logger
    _AnacondaMetrics._instance = orig_metrics
    _AnacondaTrace._instance = orig_trace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _stub_logger_instance(provider):
    """Install a stand-in _AnacondaLogger singleton owning `provider`.

    flush_telemetry() flushes the owned provider, not the OTel global.
    """
    _AnacondaLogger._instance = MagicMock(spec=_AnacondaLogger)
    _AnacondaLogger._instance._provider = provider
    return _AnacondaLogger._instance


def _make_config():
    """Build a Configuration that performs no real network I/O.

    - set_skip_internet_check(True): skip DNS / endpoint reachability probes
    - set_console_exporter(True): swap OTLP exporters for ConsoleExporter
    """
    config = Configuration(default_endpoint="http://localhost:4317")
    config.set_skip_internet_check(True)
    config.set_console_exporter(True)
    return config


def _make_attributes():
    return ResourceAttributes("test_service", "1.0.0")


def _provider_atexit_handlers():
    """Return {provider_name: atexit_handler_or_None} for the three constructed singletons.

    The SDK records the registered atexit handler on the provider instance, so this
    reflects actual behavior regardless of how each SDK module imports ``atexit``
    (``trace``/``_logs`` use ``atexit.register``; ``metrics`` uses ``from atexit import
    register``, which ``patch("atexit.register")`` cannot observe). Note the SDK's own
    attribute-name asymmetry: Tracer/Meter use ``_atexit_handler``; Logger uses
    ``_at_exit_handler``.
    """
    return {
        "TracerProvider": getattr(_AnacondaTrace._instance._provider, "_atexit_handler", None),
        "MeterProvider": getattr(_AnacondaMetrics._instance._provider, "_atexit_handler", None),
        "LoggerProvider": getattr(_AnacondaLogger._instance._provider, "_at_exit_handler", None),
    }


# ---------------------------------------------------------------------------
# (a) shutdown_on_exit=False -> no atexit registrations for any of the 3
#     SDK *Provider classes
# ---------------------------------------------------------------------------
def test_shutdown_on_exit_false_skips_atexit_registration():
    config = _make_config()
    config.set_shutdown_on_exit(False)

    initialize_telemetry(
        config=config,
        attributes=_make_attributes(),
        signal_types=["logging", "metrics", "tracing"],
    )

    handlers = _provider_atexit_handlers()
    assert handlers["TracerProvider"] is None
    assert handlers["MeterProvider"] is None
    assert handlers["LoggerProvider"] is None


# ---------------------------------------------------------------------------
# (b) Default shutdown_on_exit=True -> atexit registered for all 3 providers
# ---------------------------------------------------------------------------
def test_default_shutdown_on_exit_registers_all_three_providers():
    initialize_telemetry(
        config=_make_config(),
        attributes=_make_attributes(),
        signal_types=["logging", "metrics", "tracing"],
        # default: shutdown_on_exit=True
    )

    handlers = _provider_atexit_handlers()
    assert handlers["TracerProvider"] is not None, "TracerProvider atexit handler not set"
    assert handlers["MeterProvider"] is not None, "MeterProvider atexit handler not set"
    assert handlers["LoggerProvider"] is not None, "LoggerProvider atexit handler not set"


# ---------------------------------------------------------------------------
# (c) Global LoggerProvider retrievable via the OTel global getter after init
# ---------------------------------------------------------------------------
def test_global_logger_provider_retrievable_after_init():
    config = _make_config()
    config.set_shutdown_on_exit(False)

    initialize_telemetry(
        config=config,
        attributes=_make_attributes(),
        signal_types=["logging", "metrics", "tracing"],
    )

    lp = _logs.get_logger_provider()
    # OTel's global setter is one-shot per process: even if a prior test set
    # the global, the type contract (it's an SDK LoggerProvider) still holds.
    assert isinstance(lp, LoggerProvider)


def test_shutdown_telemetry_bounded_and_retryable_under_hanging_flush(monkeypatch):
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True
    sig._SHUTDOWN_DONE = False

    attempts = []

    def first_attempt_hangs():
        attempts.append(1)
        if len(attempts) == 1:
            time.sleep(60)
        return True

    monkeypatch.setattr(sig, "flush_telemetry", first_attempt_hangs)

    timeout = 0.3
    start = time.monotonic()
    first = sig.shutdown_telemetry(timeout_seconds=timeout)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"exceeded bound: {elapsed:.3f}s (timeout={timeout}s)"
    assert first is False
    assert sig._SHUTDOWN_DONE is False

    assert sig.shutdown_telemetry(timeout_seconds=1.0) is True
    assert sig._SHUTDOWN_DONE is True


# ---------------------------------------------------------------------------
# (e) Idempotency: subsequent shutdown_telemetry calls are immediate no-ops
# ---------------------------------------------------------------------------
def test_shutdown_telemetry_is_idempotent(monkeypatch):
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True
    sig._SHUTDOWN_DONE = False

    flush_calls = []

    def counting_flush():
        flush_calls.append(1)
        return True

    monkeypatch.setattr(sig, "flush_telemetry", counting_flush)

    # First call performs the flush
    r1 = sig.shutdown_telemetry()
    assert r1 is True
    assert len(flush_calls) == 1

    # Second call must be a no-op returning True without re-flushing
    r2 = sig.shutdown_telemetry()
    assert r2 is True
    assert len(flush_calls) == 1, (
        "shutdown_telemetry must not invoke flush_telemetry on repeat calls"
    )

    # And still a no-op if a timeout is supplied
    r3 = sig.shutdown_telemetry(timeout_seconds=0.1)
    assert r3 is True
    assert len(flush_calls) == 1


def test_shutdown_telemetry_skips_when_already_in_progress(monkeypatch):
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True
    sig._SHUTDOWN_DONE = False

    flush_calls = []

    def counting_flush():
        flush_calls.append(1)
        return True

    monkeypatch.setattr(sig, "flush_telemetry", counting_flush)

    sig._shutdown_lock.acquire()
    try:
        assert sig.shutdown_telemetry() is False
        assert flush_calls == []
    finally:
        sig._shutdown_lock.release()


# ---------------------------------------------------------------------------
# (f) Uninitialized: flush_telemetry / shutdown_telemetry return False
# ---------------------------------------------------------------------------
def test_flush_and_shutdown_return_false_when_uninitialized():
    """Without initialize_telemetry(), the public APIs must short-circuit."""
    # Fixture has already reset __ANACONDA_TELEMETRY_INITIALIZED to False.
    assert sig.__ANACONDA_TELEMETRY_INITIALIZED is False

    assert sig.flush_telemetry() is False
    assert sig.shutdown_telemetry() is False
    assert sig.shutdown_telemetry(timeout_seconds=0.1) is False


# ---------------------------------------------------------------------------
# (g) flush_telemetry calls force_flush on tracer, meter, AND logger providers
# ---------------------------------------------------------------------------
def test_flush_telemetry_invokes_force_flush_on_all_three_providers():
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True

    # spec=ClassName makes isinstance(mock, ClassName) return True, which
    # is required because flush_telemetry guards each call with isinstance.
    mock_tp = MagicMock(spec=TracerProvider)
    mock_tp.force_flush.return_value = True
    mock_mp = MagicMock(spec=MeterProvider)
    mock_mp.force_flush.return_value = True
    mock_lp = MagicMock(spec=LoggerProvider)
    mock_lp.force_flush.return_value = True
    _stub_logger_instance(mock_lp)

    with patch(
        "opentelemetry.trace.get_tracer_provider", return_value=mock_tp
    ), patch(
        "opentelemetry.metrics.get_meter_provider", return_value=mock_mp
    ):
        result = sig.flush_telemetry()

    mock_tp.force_flush.assert_called()
    mock_mp.force_flush.assert_called()
    mock_lp.force_flush.assert_called()
    assert result is True


def test_flush_telemetry_flushes_owned_logger_provider_not_the_global_one():
    """Regression: a foreign global provider must not be flushed in place of ours."""
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True

    owned_lp = MagicMock(spec=LoggerProvider)
    owned_lp.force_flush.return_value = True
    _stub_logger_instance(owned_lp)

    foreign_lp = MagicMock(spec=LoggerProvider)
    foreign_lp.force_flush.return_value = True

    with patch("opentelemetry._logs.get_logger_provider", return_value=foreign_lp):
        result = sig.flush_telemetry()

    owned_lp.force_flush.assert_called()
    foreign_lp.force_flush.assert_not_called()
    assert result is True


def test_flush_telemetry_skips_logger_provider_when_logging_not_initialized():
    """With signal_types excluding 'logging' there is no provider of ours to flush."""
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True
    _AnacondaLogger._instance = None

    foreign_lp = MagicMock(spec=LoggerProvider)

    with patch("opentelemetry._logs.get_logger_provider", return_value=foreign_lp):
        result = sig.flush_telemetry()

    foreign_lp.force_flush.assert_not_called()
    assert result is True


def test_flush_telemetry_returns_false_when_a_provider_force_flush_raises():
    """Failure on any single provider should be reflected in the return
    value, and the other providers should still be flushed."""
    sig.__ANACONDA_TELEMETRY_INITIALIZED = True

    mock_tp = MagicMock(spec=TracerProvider)
    mock_tp.force_flush.return_value = True
    mock_mp = MagicMock(spec=MeterProvider)
    mock_mp.force_flush.side_effect = RuntimeError("boom")
    mock_lp = MagicMock(spec=LoggerProvider)
    mock_lp.force_flush.return_value = True
    _stub_logger_instance(mock_lp)

    with patch(
        "opentelemetry.trace.get_tracer_provider", return_value=mock_tp
    ), patch(
        "opentelemetry.metrics.get_meter_provider", return_value=mock_mp
    ):
        result = sig.flush_telemetry()

    # Each provider's force_flush is still attempted independently.
    mock_tp.force_flush.assert_called()
    mock_mp.force_flush.assert_called()
    mock_lp.force_flush.assert_called()
    assert result is False
