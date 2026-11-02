"""Unit tests for telemetry module.

NOTE: The test conftest.py sets OTEL_SDK_DISABLED=true, which means
config.enabled is always False in this test session. The real OTel backend
never initializes during unit tests.

Tests that need to verify "enabled" behavior set _initialized=True
directly via monkeypatch to simulate an initialized backend without actually
running the OTel SDK.

Integration tests (test_telemetry_integration.py) run in a separate pytest
invocation with telemetry fully enabled against a local oteltest receiver.
"""

from __future__ import annotations

import sys
import threading
from typing import Generator

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def reset_backend(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    import anaconda_cli_base.telemetry as mod

    monkeypatch.setattr(mod, "_initialized", False)
    yield


class TestInit:
    def test_init_backend_respects_disabled_config(self) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import _ensure_initialized, config

        assert config.enabled is False
        _ensure_initialized()
        assert mod._initialized is False

    def test_init_backend_called_by_public_functions(
        self, mocker: MockerFixture
    ) -> None:
        import anaconda_cli_base.telemetry as mod

        mock_init = mocker.patch.object(mod, "_ensure_initialized")
        from anaconda_cli_base.telemetry import count

        count("x", plugin_name="test")
        mock_init.assert_called_once()

    def test_thread_safety(self) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import _ensure_initialized

        results = []

        def call_init() -> None:
            _ensure_initialized()
            results.append(mod._initialized)

        threads = [threading.Thread(target=call_init) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10


class TestNoOpWhenDisabled:
    def test_count_noop(self) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import count

        assert not mod._initialized
        count("metric", plugin_name="test")

    def test_histogram_noop(self) -> None:
        from anaconda_cli_base.telemetry import histogram

        histogram("metric", plugin_name="test", value=1.0)

    def test_log_event_noop(self) -> None:
        from anaconda_cli_base.telemetry import log_event

        log_event("body", event_name="name", plugin_name="test")

    def test_traced_yields_noop_span(self) -> None:
        from anaconda_cli_base.telemetry import traced, _NoOpSpan

        with traced("operation", plugin_name="test") as span:
            assert isinstance(span, _NoOpSpan)

    def test_get_otel_handler_returns_null_handler(self) -> None:
        import logging
        from anaconda_cli_base.telemetry import get_otel_handler

        handler = get_otel_handler()
        assert isinstance(handler, logging.NullHandler)


class TestAttrs:
    def test_build_attrs_includes_source_and_plugin(self) -> None:
        from anaconda_cli_base.telemetry import _build_attrs

        result = _build_attrs({"key": "value"}, "my-plugin")
        assert result == {
            "key": "value",
            "source": "anaconda-cli-base",
            "plugin": "my-plugin",
        }

    def test_build_attrs_handles_none(self) -> None:
        from anaconda_cli_base.telemetry import _build_attrs

        result = _build_attrs(None, "test")
        assert result == {"source": "anaconda-cli-base", "plugin": "test"}

    def test_build_attrs_does_not_mutate_input(self) -> None:
        from anaconda_cli_base.telemetry import _build_attrs

        original = {"key": "value"}
        result = _build_attrs(original, "test")
        assert "source" not in original
        assert "source" in result


class TestCommandTracking:
    def test_before_command_returns_none_when_disabled(self) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import _before_command

        assert not mod._initialized
        result = _before_command(["ai", "chat"], "anaconda")
        assert result is None

    def test_before_command_extracts_command_info(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import _before_command

        monkeypatch.setattr(mod, "_initialized", True)
        info = _before_command(
            ["ai", "chat", "--verbose", "--model=llama3"], "anaconda"
        )
        assert info is not None
        assert info.command == "ai chat"
        assert info.plugin == "ai"
        assert info.flags == "--verbose,--model"

    def test_before_command_handles_empty_args(self, monkeypatch: MonkeyPatch) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import _before_command

        monkeypatch.setattr(mod, "_initialized", True)
        info = _before_command([], "anaconda")
        assert info is not None
        assert info.command == "anaconda"
        assert info.plugin == "root"
        assert info.flags == ""

    def test_after_command_noop_when_info_is_none(self) -> None:
        from anaconda_cli_base.telemetry import _after_command

        _after_command(None, success=True)


class TestDetection:
    def test_detect_ci_vendor_github(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ci_vendor

        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert _detect_ci_vendor() == "github-actions"

    def test_detect_ci_vendor_unknown(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ci_vendor

        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setenv("CI", "true")
        assert _detect_ci_vendor() == "unknown-ci"

    def test_detect_ci_vendor_none(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ci_vendor

        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        assert _detect_ci_vendor() == ""

    def test_detect_ai_agent_opencode(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ai_agent

        monkeypatch.setenv("OPENCODE", "1")
        assert _detect_ai_agent() == "opencode"

    def test_detect_ai_agent_cursor(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ai_agent

        monkeypatch.delenv("OPENCODE", raising=False)
        monkeypatch.setenv("TERM_PROGRAM", "Cursor")
        assert _detect_ai_agent() == "cursor"

    def test_detect_ai_agent_none(self, monkeypatch: MonkeyPatch) -> None:
        from anaconda_cli_base.telemetry import _detect_ai_agent

        for var in [
            "OPENCODE",
            "CURSOR_TRACE_ID",
            "CURSOR_SESSION_ID",
            "CLINE_TASK_ID",
            "CONTINUE_GLOBAL_DIR",
            "WINDSURF_SESSION_ID",
            "CLAUDE_CODE",
        ]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("TERM_PROGRAM", "iTerm2")
        assert _detect_ai_agent() == ""

    def test_detect_tty(self) -> None:
        from anaconda_cli_base.telemetry import _detect_tty

        assert _detect_tty() is False


class TestHttpSuppression:
    def test_suppress_http_spans(self) -> None:
        from anaconda_cli_base.telemetry import suppress_http_spans, is_http_suppressed

        assert is_http_suppressed() is False
        with suppress_http_spans():
            assert is_http_suppressed() is True
        assert is_http_suppressed() is False

    def test_suppress_http_spans_nests(self) -> None:
        from anaconda_cli_base.telemetry import suppress_http_spans, is_http_suppressed

        with suppress_http_spans():
            with suppress_http_spans():
                assert is_http_suppressed() is True
            assert is_http_suppressed() is True
        assert is_http_suppressed() is False


class TestShutdownDelegation:
    def test_shutdown_telemetry_public_noop_when_disabled(self) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        assert mod._initialized is False
        shutdown_telemetry()
        shutdown_telemetry(timeout_seconds=1.0)
        assert mod._initialized is False

    def test_shutdown_telemetry_delegates_to_upstream(
        self, monkeypatch: MonkeyPatch, mocker: MockerFixture
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        monkeypatch.setattr(mod, "_initialized", True)

        fake_upstream_func = mocker.MagicMock()
        fake_module = mocker.MagicMock()
        fake_module.shutdown_telemetry = fake_upstream_func
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", fake_module)

        shutdown_telemetry(timeout_seconds=3.5)

        fake_upstream_func.assert_called_once_with(timeout_seconds=3.5)

    def test_shutdown_telemetry_uses_default_timeout_from_config(
        self, monkeypatch: MonkeyPatch, mocker: MockerFixture
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        monkeypatch.setattr(mod, "_initialized", True)

        fake_upstream_func = mocker.MagicMock()
        fake_module = mocker.MagicMock()
        fake_module.shutdown_telemetry = fake_upstream_func
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", fake_module)

        shutdown_telemetry()

        expected = mod.config.flush_timeout_ms / 1000.0
        fake_upstream_func.assert_called_once_with(timeout_seconds=expected)

    def test_shutdown_telemetry_fallback_on_import_error(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        monkeypatch.setattr(mod, "_initialized", True)
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", None)

        shutdown_telemetry(timeout_seconds=1.0)
        shutdown_telemetry()

    def test_shutdown_telemetry_swallows_upstream_exception(
        self, monkeypatch: MonkeyPatch, mocker: MockerFixture
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        monkeypatch.setattr(mod, "_initialized", True)

        fake_upstream_func = mocker.MagicMock(side_effect=RuntimeError("boom"))
        fake_module = mocker.MagicMock()
        fake_module.shutdown_telemetry = fake_upstream_func
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", fake_module)

        shutdown_telemetry(timeout_seconds=1.0)

    def test_shutdown_telemetry_does_not_acquire_init_lock(
        self, monkeypatch: MonkeyPatch, mocker: MockerFixture
    ) -> None:
        import anaconda_cli_base.telemetry as mod
        from anaconda_cli_base.telemetry import shutdown_telemetry

        monkeypatch.setattr(mod, "_initialized", True)

        fake_upstream_func = mocker.MagicMock()
        fake_module = mocker.MagicMock()
        fake_module.shutdown_telemetry = fake_upstream_func
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", fake_module)

        fail_lock = mocker.MagicMock()
        fail_lock.acquire.side_effect = AssertionError(
            "shutdown_telemetry must not acquire _lock"
        )
        fail_lock.__enter__.side_effect = AssertionError(
            "shutdown_telemetry must not enter _lock context"
        )
        monkeypatch.setattr(mod, "_lock", fail_lock)

        shutdown_telemetry(timeout_seconds=2.0)

        fake_upstream_func.assert_called_once_with(timeout_seconds=2.0)
        fail_lock.acquire.assert_not_called()
        fail_lock.__enter__.assert_not_called()
