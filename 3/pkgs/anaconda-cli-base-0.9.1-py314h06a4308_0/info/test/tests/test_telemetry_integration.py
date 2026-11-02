"""Integration tests that prove telemetry events arrive at a real OTLP receiver.

These tests use oteltest to spin up a local HTTP OTLP receiver, configure
the telemetry module to export there, and assert that data actually arrives.

Marked with @pytest.mark.integration — excluded from normal test runs by tox.
Run with: pytest -m integration
"""

from __future__ import annotations

import logging
import os
import socket
import time

import pytest

from oteltest.sink import HttpSink
from oteltest.sink.handler import AccumulatingHandler, Telemetry


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for(telemetry: Telemetry, kind: str, timeout: float = 5.0) -> None:
    attr = f"{kind}_requests"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(getattr(telemetry, attr)):
            return
        time.sleep(0.1)
    raise AssertionError(f"No {kind} received within {timeout}s")


@pytest.fixture(scope="module")
def otlp_sink():  # type: ignore[no-untyped-def]
    import anaconda_cli_base.telemetry as mod

    port = _free_port()
    handler = AccumulatingHandler()
    sink = HttpSink(handler, logging.getLogger("otelsink"), port=port, daemon=True)
    sink.start()
    time.sleep(0.3)

    os.environ["ANACONDA_TELEMETRY_ENDPOINT"] = f"http://localhost:{port}"
    os.environ["ANACONDA_TELEMETRY_ENABLED"] = "true"
    os.environ.pop("OTEL_SDK_DISABLED", None)

    mod.config.enabled = True
    mod.config.endpoint = f"http://localhost:{port}"

    mod._initialized = False
    mod._ensure_initialized()

    if not mod._initialized:
        sink.stop()
        pytest.skip(
            "Telemetry failed to initialize (anaconda-opentelemetry not available)"
        )

    yield handler

    mod.shutdown_telemetry()
    time.sleep(0.3)
    sink.stop()

    os.environ.pop("ANACONDA_TELEMETRY_ENDPOINT", None)
    os.environ.pop("ANACONDA_TELEMETRY_ENABLED", None)


@pytest.fixture()
def otlp(otlp_sink) -> Telemetry:  # type: ignore[no-untyped-def]
    return otlp_sink.telemetry


pytestmark = pytest.mark.integration


def _flush() -> None:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk._logs import LoggerProvider
    from anaconda_opentelemetry.logging import _AnacondaLogger

    tp = trace.get_tracer_provider()
    if isinstance(tp, TracerProvider):
        tp.force_flush(timeout_millis=5000)

    mp = metrics.get_meter_provider()
    if isinstance(mp, MeterProvider):
        mp.force_flush(timeout_millis=5000)

    if _AnacondaLogger._instance is not None:
        lp = _AnacondaLogger._instance._provider
        if isinstance(lp, LoggerProvider):
            lp.force_flush(timeout_millis=5000)


class TestMetrics:
    def test_count_delivers_metric(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import count

        count("test_counter", plugin_name="integration", value=3)
        _flush()
        _wait_for(otlp, "metric")

        names = set()
        for req in otlp.metric_requests:
            for rs in req.pbreq.resource_metrics:
                for sm in rs.scope_metrics:
                    for metric in sm.metrics:
                        names.add(metric.name)

        assert "test_counter" in names

    def test_histogram_delivers_metric(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import histogram

        histogram("test_duration_ms", plugin_name="integration", value=42.5)
        _flush()
        _wait_for(otlp, "metric")

        names = set()
        for req in otlp.metric_requests:
            for rs in req.pbreq.resource_metrics:
                for sm in rs.scope_metrics:
                    for metric in sm.metrics:
                        names.add(metric.name)

        assert "test_duration_ms" in names


class TestLogs:
    def test_log_event_delivers_log(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import log_event

        log_event(
            "integration test event",
            event_name="test_event",
            plugin_name="integration",
            attributes={"key": "value"},
        )
        _flush()
        _wait_for(otlp, "log")

        bodies = []
        for req in otlp.log_requests:
            for rs in req.pbreq.resource_logs:
                for sl in rs.scope_logs:
                    for record in sl.log_records:
                        bodies.append(record.body.string_value)

        assert "integration test event" in bodies

    def test_otel_log_handler_delivers_log(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import get_otel_handler

        test_logger = logging.getLogger("integration_test_logger")
        handler = get_otel_handler(level=logging.WARNING)
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.WARNING)

        test_logger.warning("handler integration test warning")
        _flush()
        _wait_for(otlp, "log")

        bodies = []
        for req in otlp.log_requests:
            for rs in req.pbreq.resource_logs:
                for sl in rs.scope_logs:
                    for record in sl.log_records:
                        bodies.append(record.body.string_value)

        assert "handler integration test warning" in bodies
        test_logger.removeHandler(handler)


class TestTracing:
    def test_traced_delivers_span(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import traced

        with traced(
            "test_operation", plugin_name="integration", attributes={"step": "1"}
        ):
            time.sleep(0.01)

        _flush()
        _wait_for(otlp, "trace")

        span_names = set()
        for req in otlp.trace_requests:
            for rs in req.pbreq.resource_spans:
                for ss in rs.scope_spans:
                    for span in ss.spans:
                        span_names.add(span.name)

        assert "test_operation" in span_names


class TestResourceAttributes:
    def test_resource_attributes_are_correct(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import count

        count("resource_attr_test", plugin_name="integration")
        _flush()
        _wait_for(otlp, "metric")

        resource_attrs = {}
        for req in otlp.metric_requests:
            for rs in req.pbreq.resource_metrics:
                for attr in rs.resource.attributes:
                    resource_attrs[attr.key] = attr.value

        assert resource_attrs["service.name"].string_value == "anaconda-cli-base"
        assert resource_attrs["environment"].string_value == "production"
        assert "platform" in resource_attrs
        assert len(resource_attrs["platform"].string_value) > 0


class TestCLIIntegration:
    def test_cli_command_delivers_metrics(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import _before_command
        from anaconda_opentelemetry import increment_counter, record_histogram

        info = _before_command(["test", "subcommand"], "anaconda")
        assert info is not None
        from typing import Any

        duration_ms = (time.perf_counter() - info.start_time) * 1000
        attrs: dict[str, Any] = {
            "command": info.command,
            "plugin": info.plugin,
            "source": "anaconda-cli-base",
            "flags": info.flags,
            "exit_code": 0,
        }
        record_histogram("cli_command_duration_ms", duration_ms, attrs)
        increment_counter("cli_command_invoked", attributes=attrs)

        _flush()
        _wait_for(otlp, "metric")

        names = set()
        for req in otlp.metric_requests:
            for rs in req.pbreq.resource_metrics:
                for sm in rs.scope_metrics:
                    for metric in sm.metrics:
                        names.add(metric.name)

        assert "cli_command_duration_ms" in names
        assert "cli_command_invoked" in names


class TestBackendInit:
    def test_multiple_calls_share_single_backend(self, otlp: Telemetry) -> None:
        from anaconda_cli_base.telemetry import count, is_telemetry_enabled

        assert is_telemetry_enabled()

        count("from_first_call", plugin_name="plugin-a")
        count("from_second_call", plugin_name="plugin-b")
        _flush()
        _wait_for(otlp, "metric")

        names = set()
        for req in otlp.metric_requests:
            for rs in req.pbreq.resource_metrics:
                for sm in rs.scope_metrics:
                    for metric in sm.metrics:
                        names.add(metric.name)

        assert "from_first_call" in names
        assert "from_second_call" in names
