"""Unit tests for the lifecycle module.

NOTE: The test conftest.py sets OTEL_SDK_DISABLED=true, but these tests
operate at the module-state level and do not actually exercise the OTel
backend. Real os._exit and threading.Timer are patched out for safety.
"""

from __future__ import annotations

import signal
import sys
from typing import Generator, List
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

import anaconda_cli_base.lifecycle as mod


@pytest.fixture(autouse=True)
def reset_lifecycle(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Reset module-level state before every test."""
    monkeypatch.setattr(mod, "_triggered", False)
    monkeypatch.setattr(mod, "_handlers_installed", False)
    monkeypatch.setattr(mod, "_hooks", [])
    yield


@pytest.fixture(autouse=True)
def safe_force_exit(mocker: MockerFixture) -> MagicMock:
    """Safety net so os._exit cannot run from tests."""
    return mocker.patch("anaconda_cli_base.lifecycle.os._exit")


@pytest.fixture
def fake_timer(mocker: MockerFixture) -> MagicMock:
    """Patch threading.Timer so the watchdog never fires."""
    return mocker.patch("anaconda_cli_base.lifecycle.threading.Timer")


@pytest.fixture
def mock_shutdown_telemetry(mocker: MockerFixture) -> MagicMock:
    """Patch the public telemetry shutdown to avoid OTel imports."""
    return mocker.patch("anaconda_cli_base.telemetry.shutdown_telemetry")


class TestRegisterShutdownHook:
    def test_hooks_run_in_registration_order(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        order: List[str] = []
        mod.register_shutdown_hook(lambda: order.append("first"))
        mod.register_shutdown_hook(lambda: order.append("second"))
        mod.register_shutdown_hook(lambda: order.append("third"))

        mod.trigger_shutdown()

        assert order == ["first", "second", "third"]

    def test_register_appends_to_hooks_list(self) -> None:
        def hook() -> None:
            pass

        assert mod._hooks == []
        mod.register_shutdown_hook(hook)
        assert mod._hooks == [hook]


class TestTriggerShutdownIdempotency:
    def test_second_call_is_noop(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        counter = {"n": 0}

        def hook() -> None:
            counter["n"] += 1

        mod.register_shutdown_hook(hook)

        mod.trigger_shutdown()
        mod.trigger_shutdown()

        assert counter["n"] == 1
        assert fake_timer.call_count == 1
        assert mock_shutdown_telemetry.call_count == 1

    def test_only_one_watchdog_timer_started(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        for _ in range(5):
            mod.trigger_shutdown()

        assert fake_timer.call_count == 1
        timer_instance = fake_timer.return_value
        assert timer_instance.start.call_count == 1


class TestTriggerShutdownTelemetry:
    def test_calls_shutdown_telemetry_with_2s_timeout(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        mod.trigger_shutdown()

        mock_shutdown_telemetry.assert_called_once_with(timeout_seconds=2.0)

    def test_does_not_acquire_telemetry_lock(
        self,
        fake_timer: MagicMock,
        monkeypatch: MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        import anaconda_cli_base.telemetry as tel

        monkeypatch.setattr(tel, "_initialized", True)

        fake_upstream = mocker.MagicMock()
        fake_upstream.shutdown_telemetry = mocker.MagicMock()
        monkeypatch.setitem(sys.modules, "anaconda_opentelemetry", fake_upstream)

        fail_lock = mocker.MagicMock()
        fail_lock.acquire.side_effect = AssertionError(
            "trigger_shutdown must not acquire telemetry._lock"
        )
        fail_lock.__enter__.side_effect = AssertionError(
            "trigger_shutdown must not enter telemetry._lock context"
        )
        monkeypatch.setattr(tel, "_lock", fail_lock)

        mod.trigger_shutdown()

        fail_lock.acquire.assert_not_called()
        fail_lock.__enter__.assert_not_called()

    def test_hook_exception_does_not_stop_shutdown(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        ran: List[str] = []

        def boom() -> None:
            raise RuntimeError("boom")

        def ok() -> None:
            ran.append("ok")

        mod.register_shutdown_hook(boom)
        mod.register_shutdown_hook(ok)

        mod.trigger_shutdown()

        assert ran == ["ok"]
        mock_shutdown_telemetry.assert_called_once_with(timeout_seconds=2.0)

    def test_telemetry_shutdown_exception_swallowed(
        self,
        fake_timer: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "anaconda_cli_base.telemetry.shutdown_telemetry",
            side_effect=RuntimeError("upstream blew up"),
        )

        mod.trigger_shutdown()

    def test_watchdog_timer_started_before_hooks_run(
        self,
        fake_timer: MagicMock,
        mock_shutdown_telemetry: MagicMock,
    ) -> None:
        events: List[str] = []

        timer_instance = fake_timer.return_value
        timer_instance.start.side_effect = lambda: events.append("timer_started")

        def hook() -> None:
            events.append("hook_ran")

        mod.register_shutdown_hook(hook)
        mod.trigger_shutdown()

        assert events == ["timer_started", "hook_ran"]


class TestLongRunningDecorator:
    def test_decoration_does_not_install_signal_handlers(
        self, mocker: MockerFixture
    ) -> None:
        signal_signal = mocker.patch("anaconda_cli_base.lifecycle.signal.signal")

        @mod.long_running
        def cmd() -> str:
            return "ran"

        assert signal_signal.call_count == 0
        assert mod._handlers_installed is False

    def test_invocation_installs_signal_handlers(self, mocker: MockerFixture) -> None:
        signal_signal = mocker.patch("anaconda_cli_base.lifecycle.signal.signal")

        @mod.long_running
        def cmd() -> str:
            return "ran"

        result = cmd()

        assert result == "ran"
        assert signal_signal.call_count >= 1
        assert mod._handlers_installed is True

    def test_repeated_invocation_only_installs_once(
        self, mocker: MockerFixture
    ) -> None:
        signal_signal = mocker.patch("anaconda_cli_base.lifecycle.signal.signal")

        @mod.long_running
        def cmd() -> None:
            pass

        cmd()
        first_count = signal_signal.call_count
        cmd()
        cmd()

        assert signal_signal.call_count == first_count

    def test_module_import_does_not_register_signals(self) -> None:
        assert mod._handlers_installed is False
        assert mod._hooks == []
        assert mod._triggered is False

    def test_signal_handler_install_failure_is_swallowed(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "anaconda_cli_base.lifecycle.signal.signal",
            side_effect=ValueError("not on main thread"),
        )

        @mod.long_running
        def cmd() -> str:
            return "ran"

        result = cmd()
        assert result == "ran"
        assert mod._handlers_installed is False


class TestForceExit:
    @pytest.mark.parametrize(
        ("signum", "expected_code"),
        [
            (signal.SIGTERM, 143),
            (signal.SIGINT, 130),
            (None, 143),
        ],
    )
    def test_force_exit_maps_signum_to_exit_code(
        self,
        safe_force_exit: MagicMock,
        signum: int | None,
        expected_code: int,
    ) -> None:
        mod._force_exit(signum)

        safe_force_exit.assert_called_once_with(expected_code)

    def test_force_exit_distinguishes_signum_zero_from_missing(
        self,
        safe_force_exit: MagicMock,
    ) -> None:
        mod._force_exit(0)

        safe_force_exit.assert_called_once_with(128)
