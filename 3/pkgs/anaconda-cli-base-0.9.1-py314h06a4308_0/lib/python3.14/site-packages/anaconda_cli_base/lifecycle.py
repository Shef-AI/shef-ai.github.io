"""Long-running command lifecycle management for anaconda-cli-base.

Provides signal handling, shutdown hooks, bounded telemetry flush, and a
process-exit watchdog for CLI commands that block indefinitely (e.g., servers).

Short-lived commands do not need this module — they exit cleanly via
``_after_command`` which handles telemetry flush automatically.
"""

import functools
import logging
import os
import signal
import threading
from types import FrameType
from typing import Any, Callable, List, Optional

from anaconda_cli_base import telemetry

logger = logging.getLogger(__name__)

WATCHDOG_DEADLINE_SECS: float = 10.0
"""Safety-net timeout. After trigger_shutdown() fires, if the process hasn't
exited within this many seconds, os._exit(143) forces termination."""

_hooks: List[Callable[[], None]] = []
_triggered: bool = False
_trigger_lock = threading.Lock()


def register_shutdown_hook(hook: Callable[[], None]) -> None:
    """Register a callable to run when shutdown is triggered.

    Hooks run in registration order. They should be fast (milliseconds)
    and non-blocking — use them to set events, close pipes, etc.

    Not idempotent: each call appends another hook. Register a given
    hook once (typically at startup).
    """
    _hooks.append(hook)


def trigger_shutdown(signum: Optional[int] = None) -> None:
    """Trigger the shutdown sequence. Idempotent.

    1. Starts the watchdog timer FIRST (so nothing below can prevent it).
    2. Runs all registered hooks in order (each wrapped in try/except).
    3. Calls shutdown_telemetry with a 2-second bound.

    Does NOT call os._exit itself — lets normal unwinding continue.
    The watchdog fires os._exit(128 + signum) only if unwinding stalls.
    """
    global _triggered
    with _trigger_lock:
        if _triggered:
            return
        _triggered = True

    # Start watchdog FIRST — ordering invariant from anaconda-mcp's design
    timer = threading.Timer(WATCHDOG_DEADLINE_SECS, _force_exit, args=(signum,))
    timer.daemon = True
    timer.start()

    # Run hooks in registration order
    for hook in _hooks:
        try:
            hook()
        except Exception:
            logger.debug("Shutdown hook %r failed", hook, exc_info=True)

    try:
        telemetry.shutdown_telemetry(timeout_seconds=2.0)
    except Exception:
        logger.debug("Telemetry shutdown in trigger_shutdown failed", exc_info=True)


def _force_exit(signum: Optional[int] = None) -> None:
    """Last-resort process termination. Fires from the watchdog timer."""
    os._exit(128 + signum if signum is not None else 143)


def long_running(func: Callable) -> Callable:
    """Decorator marking a CLI command as long-running.

    On invocation, installs SIGTERM and SIGINT handlers that call
    trigger_shutdown(signum). The original signal behavior (KeyboardInterrupt
    for SIGINT) is preserved after trigger_shutdown runs.

    Idempotent: re-applying is a no-op. Windows-safe (guards on signal
    availability).
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _install_signal_handlers()
        return func(*args, **kwargs)

    return wrapper


_handlers_installed: bool = False


def _install_signal_handlers() -> None:
    """Install SIGTERM/SIGINT handlers. Idempotent."""
    global _handlers_installed
    if _handlers_installed:
        return

    def _signal_handler(signum: int, frame: Optional[FrameType]) -> None:
        trigger_shutdown(signum)
        # For SIGINT, raise KeyboardInterrupt so normal unwinding proceeds
        if signum == signal.SIGINT:
            raise KeyboardInterrupt

    try:
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
        _handlers_installed = True
    except (OSError, ValueError):
        # Not on main thread or unsupported platform
        logger.debug("Could not install signal handlers", exc_info=True)
