# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# signals.py
"""
Anaconda Telemetry - Metrics Module

This module provides functionality for logging, metrics, and tracing (together called
signals) using OpenTelemetry. It includes classes for handling logging, metrics, and
tracing, as well as functions for initializing the telemetry system and recording metrics.
"""

import logging, socket, threading
from typing import Dict, Iterator, List, Optional
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

from ._compat import OTEL_PRIVATE_LOGS_AVAILABLE, LoggingHandler

from .config import Configuration as Config
from .attributes import ResourceAttributes as Attributes
from .formatting import AttrDict

from .common import MetricsNotInitialized
from .logging import _AnacondaLogger
from .metrics import _AnacondaMetrics
from .tracing import _AnacondaTrace, _ASpan


_SUPPRESSED_LOGGER_ROOTS = ('opentelemetry',)


def _suppress_otel_export_errors():
    for root in _SUPPRESSED_LOGGER_ROOTS:
        logging.getLogger(root).setLevel(logging.CRITICAL)
        prefix = root + '.'
        for name, logger in list(logging.Logger.manager.loggerDict.items()):
            if name.startswith(prefix) and isinstance(logger, logging.Logger):
                logger.setLevel(logging.NOTSET)


# Internet and endpoint access check method
def __check_internet_status(config: Config, timeout: float = 5.0) -> tuple[bool,bool]: # seconds max to pause....
    # Relies on Configuration to validate the endpoint...
    internet = True
    access = True
    if config._get_skip_internet_check():
        return True, True
    endpoint = config._get_default_endpoint()
    try:
        # Access to a highly available DNS site...
        socket.create_connection(('8.8.8.8', 53), timeout=timeout / 2).close()
    except OSError:
        logging.getLogger(__package__).warning("Anaconda OpenTelemetry: No Internet was detected!")
        internet = False  # No internet, but internet is not an absolute requirement for on-prem solutions.
    try:
        socket.create_connection((config._endpoints['default_endpoint'].host, config._endpoints['default_endpoint']._internet_check_port), timeout=timeout / 2).close()
    except OSError:
        logging.getLogger(__package__).fatal(f"Anaconda OpenTelemetry: No access to the endpoint '{endpoint}'!")
        access = False # This could be fatal, not endpoint for telemetry.
    if access == True:
        logging.getLogger(__package__).info(f"Anaconda OpenTelemetry: Successful access to the endpoint '{endpoint}'!")
    return internet, access

__ANACONDA_TELEMETRY_INITIALIZED = False
__SIGNALS = None
__CONFIG = None


################################################################################
# Exposed APIs
def initialize_telemetry(config: Config,
                         attributes: Attributes = None,
                         signal_types: List[str] = ['metrics']):
    """
    Initializes the telemetry system.

    Args:
        service_name (str): The name of the service.
        service_version (str): The version of the service.
        config (Configuration): The configuration for the telemetry. At a minimum, the Configuration must have a default endpoint
            for connection to the collector.
        attributes (ResourceAttributes, optional): A class containing common attributes. If provided,
            it will override any values shared with configuration file.
        signal_types (list, optional): List of metric types to initialize. Defaults to ['logging','metrics','tracing'].
            Supported values are 'logging', 'metrics', and 'tracing'. If an empty list is provided, no metrics will be initialized.

    Raises:
        ValueError: If the config passed is None or the attributes passed are None.
    """
    global __ANACONDA_TELEMETRY_INITIALIZED
    global __SIGNALS
    global __CONFIG

    if __ANACONDA_TELEMETRY_INITIALIZED is True:
        return  # Already initialized
    if config is None:
        raise ValueError(f"The config argument is required but was None")
    if attributes is None:
        raise ValueError(f"The attributes argument is required but was None")

    __CONFIG = config
    __SIGNALS = signal_types

    if type(attributes.parameters) != dict:
        raise ValueError(f"The parameters attribute in ResourceAttributes must be a dictionary")

    if not config._get_verbose_export_errors():
        _suppress_otel_export_errors()

    # Right now, no action is taken but it possible to disable telemetry with no access to the endpoint...
    _, _ = __check_internet_status(config, timeout=4)  # Max wait 4 seconds...

    # all params are the same currently so only write them once
    init_params = (config, attributes)

    # Initialize logging here...
    signal_type_count = 0
    if 'logging' in signal_types:
        # The OTel logs SDK lives behind a private namespace; _compat degrades to
        # no-ops if it ever disappears. Skip the signal rather than wire up
        # inert objects the caller would have to debug.
        if OTEL_PRIVATE_LOGS_AVAILABLE:
            _AnacondaLogger._instance = _AnacondaLogger(*init_params)
            signal_type_count += 1
        else:
            logging.getLogger(__package__).warning(
                "Anaconda OpenTelemetry: the 'logging' signal was requested but the "
                "installed opentelemetry-sdk does not provide the required logs API. "
                "Skipping log telemetry."
            )

    # Initialize the telemetry system here
    if 'metrics' in signal_types:
        _AnacondaMetrics._instance = _AnacondaMetrics(*init_params)
        signal_type_count += 1

    # Initialize tracing here...
    if 'tracing' in signal_types:
        _AnacondaTrace._instance = _AnacondaTrace(*init_params)
        signal_type_count += 1

    if signal_type_count == 0:
        logging.getLogger(__package__).warning(
            "No signal types were initialized. Was this intended? If not please check the " +
              "'metrics' section in the configuration file and/or the list of " +
              "metric types in the parameter 'signal_types'."
        )
    __ANACONDA_TELEMETRY_INITIALIZED = True

_SHUTDOWN_DONE = False
_shutdown_lock = threading.Lock()


def flush_telemetry() -> bool:
    """Force-flush the providers this package emits through.

    Spans and metrics are recorded via the OTel globals, so the global getters are correct
    for them. Log records are not: send_event and get_telemetry_logger_handler write to the
    LoggerProvider owned by _AnacondaLogger, which is not the global one when another
    library set that first, so the owned provider is flushed instead.

    Returns True if every provider we own flushed successfully.
    """
    if not __ANACONDA_TELEMETRY_INITIALIZED:
        return False
    success = True
    try:
        tp = trace.get_tracer_provider()
        if isinstance(tp, TracerProvider):
            try:
                tp.force_flush()
            except Exception:
                logging.getLogger(__package__).debug("Tracer flush failed", exc_info=True)
                success = False

        mp = metrics.get_meter_provider()
        if isinstance(mp, MeterProvider):
            try:
                mp.force_flush()
            except Exception:
                logging.getLogger(__package__).debug("Meter flush failed", exc_info=True)
                success = False

        if _AnacondaLogger._instance is not None:
            lp = _AnacondaLogger._instance._provider
            try:
                lp.force_flush()
            except Exception:
                logging.getLogger(__package__).debug("Logger flush failed", exc_info=True)
                success = False
    except Exception:
        logging.getLogger(__package__).debug("flush_telemetry failed", exc_info=True)
        success = False
    return success


def shutdown_telemetry(*, timeout_seconds: Optional[float] = None) -> bool:
    """Flush all telemetry providers at process shutdown, optionally time-bounded.

    Performs a bounded *force-flush* (via :func:`flush_telemetry`). It intentionally does
    not call ``provider.shutdown()``: at process exit that only adds worker-thread joins
    (more blocking) with no benefit. Pair with
    ``config.set_shutdown_on_exit(False)`` to control flush timing from a
    signal handler or atexit path.

    With ``timeout_seconds=None`` the flush runs synchronously (unbounded). When set, the
    flush runs on a daemon thread joined for at most ``timeout_seconds``; only the
    caller's wait is bounded (a still-running flush thread is reaped at interpreter exit).

    Idempotent and thread-safe: once a flush completes it is not repeated; concurrent or
    re-entrant (signal-handler) calls never double-flush or block. A call that times out
    does not mark completion, so a later call may retry.

    The ``join`` blocks the calling thread, so do not call this with a ``timeout_seconds``
    from inside an async event loop; use it from a signal handler, an atexit path, or a
    dedicated thread.

    Returns True if the flush completed (now or previously); False if telemetry was never
    initialized, the flush timed out, or another call is already in progress.
    """
    global _SHUTDOWN_DONE
    if not __ANACONDA_TELEMETRY_INITIALIZED:
        return False
    if _SHUTDOWN_DONE:
        return True
    # Non-blocking so a concurrent or re-entrant caller returns immediately instead of
    # double-flushing or deadlocking (this may run inside a signal handler).
    if not _shutdown_lock.acquire(blocking=False):
        return _SHUTDOWN_DONE
    try:
        if _SHUTDOWN_DONE:
            return True
        if timeout_seconds is None:
            completed = flush_telemetry()
        else:
            flush_thread = threading.Thread(target=flush_telemetry, daemon=True)
            flush_thread.start()
            flush_thread.join(timeout=timeout_seconds)
            completed = not flush_thread.is_alive()
        if completed:
            _SHUTDOWN_DONE = True
        return completed
    finally:
        _shutdown_lock.release()


def change_signal_endpoint(signal_type: str,
                           new_endpoint: str,
                           auth_token: str = None):
    """
    Updates the endpoint for the passed signal

    Args:
        signal_type (str): signal type to update endpoint for. Supported values are 'logging', 'metrics', and 'tracing'

    Returns:
        boolean: value indicating whether the update was successful or not
    """
    if signal_type.lower() == 'metrics':
        _AnacondaTelInstance = _AnacondaMetrics
        batch_access = _AnacondaTelInstance._instance.metric_reader
    elif signal_type.lower() == 'tracing':
        _AnacondaTelInstance = _AnacondaTrace
        batch_access = _AnacondaTelInstance._instance._processor
    elif signal_type.lower() == 'logging':
        _AnacondaTelInstance = _AnacondaLogger
        batch_access = _AnacondaTelInstance._instance._processor
    else:
        logging.getLogger(__package__).warning(f"{signal_type} not a valid signal type.")
        return False

    # execute OpenTelemetry changes
    updated_endpoint = _AnacondaTelInstance._instance.exporter.change_signal_endpoint(
        batch_access,
        _AnacondaTelInstance._instance._config,
        new_endpoint,
        auth_token=auth_token
    )

    if not updated_endpoint:
        logging.getLogger(__package__).warning(f"Endpoint for {signal_type} failed to update.")
        return False
    else:
        logging.getLogger(__package__).info(f"Endpoint for {signal_type} was successfully updated.")
    return True

def record_histogram(metric_name, value, attributes: AttrDict={}) -> bool:
    """
    Records a increasing only metric with the given name and value. The value will
    always appear in the attributes section in the raw OTLP output and the timestamp
    will be the histogram value.

    Will catch any exceptions generated by metric usage.

    Args:
        metric_name (str): The name of the metric.
        value (float): The value of the metric. Can be any float since the timestamp is the ever increasing value of the histogram.
        attributes (dict, optional): Additional attributes for the metric. Defaults to {}.

    Returns:
        bool: True if the metric was recorded successfully, False otherwise (logging the error).
    """
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        return False
    try:
        return _AnacondaMetrics._instance.record_histogram(metric_name, value, _AnacondaMetrics._instance._process_attributes(attributes))
    except MetricsNotInitialized as me:
        logging.getLogger(__package__).warning(f"An attempt was made to record a histogram metric when metrics were not configured.")
        return False
    except Exception as e:
        logging.getLogger(__package__).error(f"UNCAUGHT EXCEPTION:\n{e}")
        return False

def set_gauge(metric_name, value, attributes: AttrDict={}) -> bool:
    """
    Sets a gauge metric with the given name to the given value. A gauge records the last
    value set rather than a sum, so it is the right choice for values that go up and down
    and are sampled rather than accumulated (queue depth, memory in use, temperature).

    Will catch any exceptions generated by metric usage.

    Args:
        metric_name (str): The name of the metric.
        value (int | float): The current value of the metric. Must be an int or a float; negative
            values are allowed. A value of any other type (including None and bool) is rejected.
        attributes (dict, optional): Additional attributes for the metric. Defaults to {}.

    Returns:
        bool: True if the metric was recorded successfully, False otherwise (logging the error).
    """
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        return False
    try:
        return _AnacondaMetrics._instance.set_gauge(metric_name, value, _AnacondaMetrics._instance._process_attributes(attributes))
    except MetricsNotInitialized:
        logging.getLogger(__package__).warning("An attempt was made to set a gauge metric when metrics were not configured.")
        return False
    except Exception as e:
        logging.getLogger(__package__).error(f"UNCAUGHT EXCEPTION:\n{e}")
        return False

def increment_counter(counter_name, by=1, attributes: AttrDict={}) -> bool:
    """
    Increments a counter or up down counter by the given parameter 'by'.

    Will catch any exceptions generated by metric usage.

    Args:
        counter_name (str): The name of the counter.
        by (int, optional): The value to increment by. Defaults to 1. The abs(by) is used to protect from negative numbers.
        attributes (dict, optional): Additional attributes for the counter. Defaults to {}.

    Returns:
        bool: True if the counter was incremented successfully, False otherwise (logging the error).
    """
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        return False
    try:
        return _AnacondaMetrics._instance.increment_counter(counter_name, by, _AnacondaMetrics._instance._process_attributes(attributes))
    except MetricsNotInitialized:
        logging.getLogger(__package__).warning(f"An attempt was made to change/create a counter metric when metrics were not configured.")
        return False
    except Exception as e:
        logging.getLogger(__package__).error(f"UNCAUGHT EXCEPTION:\n{e}")
        return False

def decrement_counter(counter_name, by=1, attributes: AttrDict={}) -> bool:
    """
    Decrements a up down counter with the given name and value. If applied to a regular counter it will log a warning and silently fail.

    Will catch any exceptions generated by metric usage.

    Args:
        counter_name (str): The name of the counter.
        by (int, optional): The value to decrement by. Defaults to 1. abs(by) is used to protect from negative numbers.
        attributes (dict, optional): Additional attributes for the counter. Defaults to {}.

    Returns:
        bool: True if the counter was decremented successfully, False otherwise (logging the error).
    """
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        return False
    try:
        return _AnacondaMetrics._instance.decrement_counter(counter_name, by, _AnacondaMetrics._instance._process_attributes(attributes))
    except MetricsNotInitialized:
        logging.getLogger(__package__).warning(f"An attempt was made to change/create a counter metric when metrics were not configured.")
        return False
    except Exception as e:
        logging.getLogger(__package__).error(f"UNCAUGHT EXCEPTION:\n{e}")
        return False

@contextmanager
def get_trace(name: str, attributes: AttrDict = {}, carrier: Dict[str,str] = None) -> Iterator[_ASpan]:
    """
    Create or continue a named trace (based on the 'carrier' parameter).

    Use the function like a Python I/O object (keyword 'with') to ensure the span is closed properly.

    Will catch any exceptions generated by tracing usage.

    Args:
        name (str): The name of the trace.
        attributes (dict, optional): Additional attributes for the trace.  Defaults to {}.
        carrier (dict, optional): The carrier used to continue a trace context in the output data. Defaults to None.

    Example:
        with get_trace("my_trace_name", {"key": "value"}) as span:
            # Do some work here
            pass
            # The span will be closed automatically when exiting the 'with' block.

    Returns:
        Iterator[Tracer]: An iterator for the tracer.
    """
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        return None

    try:
        aspan = _AnacondaTrace._instance.get_span(name, _AnacondaTrace._instance._process_attributes(attributes), carrier)
    except:  # Trace is different than the other signals, there is no easy way to log and continue.
        logging.getLogger(__package__).warning(f"Attempt to trace a with-block when tracing was not configured.")
        aspan = _ASpan("UNKNOWN", span=None, noop=True)
    try:
        yield aspan
    except Exception as e:
        aspan.add_exception(e)
        aspan.set_error_status()
        _AnacondaTrace._instance.logger.error(f"Error in trace span {name}: {e}")
    finally:
        aspan._close()

def get_telemetry_logger_handler() -> LoggingHandler:
    """
    Returns the telemetry logger handler. This lets the package user control how the application uses the telemetry logger.
    Insert this handler into your named logger.

        log = logging.getLogger("my_logger")
        log.addHandler(get_telemetry_logger_handler())

    Previously, this was injected into the root logger, but this turned out to be problematic for some applications that
    wanted to control the logging configuration more precisely. This injection behavior is now disabled. If you wish to
    inject the handler into the root logger, you can do so manually. See the Python logging documentation for more information.

    Returns:
        logging.Logger: The telemetry logger handler if logging was enabled via signal_types in initialize_telemetry,
        otherwise this function returns None.
    Raises:
        RuntimeError: if `initialize_telemetry` has not been called
    """
    global __ANACONDA_TELEMETRY_INITIALIZED
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")  # Since init didn't happen this is not exported in OTel!!!
        raise RuntimeError("Anaconda telemetry system not initialized.")
    if _AnacondaLogger._instance is not None:
        return _AnacondaLogger._instance._get_log_handler()
    return None  # No logger handler available, logging not initialized or not configured.

def send_event(body: str, event_name: str, attributes: AttrDict={}) -> bool:
    """
    Sends a log event directly to the OpenTelemetry pipeline without using Python's logging module.
    This is useful when you want to export log telemetry but don't want the output mixing with
    your application's output or developer logs.

    Params:
        body (str): the log message body
        event_name (str): mandatory event name added to attributes
        attributes (AttrDict): optional attributes dict
    Returns:
        bool: True if the event was sent, False if logging was not initialized
    Raises:
        RuntimeError: if `initialize_telemetry` has not been called
    """
    global __ANACONDA_TELEMETRY_INITIALIZED
    if __ANACONDA_TELEMETRY_INITIALIZED is False:
        logging.getLogger(__package__).error("Anaconda telemetry system not initialized.")
        raise RuntimeError("Anaconda telemetry system not initialized.")
    if _AnacondaLogger._instance is not None:
        event_logger = _AnacondaLogger._instance._get_event_logger()
        event_logger._send_event(body, event_name, _AnacondaLogger._instance._process_attributes(attributes))
        return True
    return False