# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# tracing.py
"""
Anaconda Telemetry - Tracing signal class and span classes.
"""

import logging
from typing import Dict, Optional
from abc import ABC

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.propagate import get_global_textmap
from opentelemetry.trace.status import StatusCode

from .common import _AnacondaCommon
from .config import Configuration as Config
from .attributes import ResourceAttributes as Attributes
from .exporter_shim import OTLPSpanExporterShim
from .formatting import AttrDict


class ASpan(ABC):
    """
    Abstract base class for a span in the tracing system. This class should not be instantiated directly.
    Use the get_trace function to create an instance of this class.
    """
    def add_event(self, name: str, attributes: AttrDict = None) -> None:
        """
        Add an event to the span with the given name and attributes.

        Args:
            name (str): The name of the event.
            attributes (dict, optional): Additional attributes for the event. Defaults to None.
        """
        pass

    def add_exception(self, exception: Exception) -> None:
        """
        Add an exception to the span. If the exception is None, a generic exception is recorded.

        Args:
            exception (Exception): The exception to add to the span.
        """
        pass

    def set_error_status(self, msg: Optional[str] = None) -> None:
        """
        Set the status of the span to ERROR. This indicates that an error occurred during the span's execution.

        Args:
            msg (str, optional): An optional message to include in the error status. Defaults to None.
        """
        pass

    def add_attributes(self, attributes: AttrDict) -> None:
        """
        Adds attributes for the span (adds to the orginal attribute on creation of the span).

        Args:
            attributes (dict): A dictionary of attributes to add for the span.
        """
        pass


class _ASpan(ASpan):
    # A single class for the tracing yielded return value.
    def __init__(self, name: str, span: trace.Span, attributes: AttrDict = {}, noop: bool = False) -> None:
        self._noop = noop
        self._name = name
        self._attributes: AttrDict = attributes
        self._span: trace.Span = span

    def add_event(self, name: str, attributes: AttrDict = None) -> None:
        if self._noop: return
        if attributes is None:
            attributes = {}
        self._span.add_event(f"{self._name}.{name}", attributes=attributes)

    def add_exception(self, exception: Exception) -> None:
        if self._noop: return
        if exception is None:
            exception = Exception("Generic exception because the exception passed was None.")

        self._span.record_exception(exception,
                                    attributes={
                                        "exception.type": type(exception).__name__,
                                        "exception.message": str(exception)
                                    })

    def set_error_status(self, msg: Optional[str] = None) -> None:
        if self._noop: return
        self._span.set_status(StatusCode.ERROR, msg if msg else "An error occurred during the span's execution.")

    def add_attributes(self, attributes: AttrDict) -> None:
        if self._noop: return
        if not isinstance(attributes, dict):
            raise TypeError("Attributes must be a dictionary of string key and string values.")
        self._attributes.update(attributes)
        self._span.set_attributes(self._attributes)

    def _close(self) -> None:
        if self._noop: return
        self._span.end()


class _AnacondaTrace(_AnacondaCommon):
    # Singleton instance (internal only); provide a single instance of the tracing class
    _instance = None

    def __init__(self, config: Config, attributes: Attributes):
        # Init singleton instance
        super().__init__(config, attributes)
        self.telemetry_export_interval_millis = config._get_tracing_export_interval_ms()
        self.tracing_endpoint = config._get_tracing_endpoint()

        self.tracer = self._setup_tracing(config)

    def _setup_tracing(self, config: Config) -> trace.Tracer:
        # Create tracer provider
        tracer_provider = TracerProvider(resource=self.resource, shutdown_on_exit=self._shutdown_on_exit)

        # Add OTLP exporter
        if self.use_console_exporters:
            exporter = ConsoleSpanExporter()
        else:
            auth_token = config._get_auth_token_tracing()
            headers: Dict[str, str] = {}
            if auth_token is not None:
                headers['authorization'] = f'Bearer {auth_token}'
            if config._get_request_protocol_tracing() in ['grpc', 'grpcs']:  # gRPC
                insecure = not config._get_TLS_tracing()
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPSpanExportergRPC
                exporter = OTLPSpanExporterShim(
                    OTLPSpanExportergRPC,
                    endpoint=self.tracing_endpoint,
                    insecure=insecure,
                    credentials=config._get_ca_cert_tracing() if not insecure else None,
                    headers=headers
                )
            else:  # HTTP
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP
                http_kwargs = self._build_http_exporter_kwargs('tracing', self.tracing_endpoint, headers)
                exporter = OTLPSpanExporterShim(
                    OTLPSpanExporterHTTP,
                    **http_kwargs
                )

        self.exporter = exporter
        self._processor = BatchSpanProcessor(self.exporter, schedule_delay_millis=self.telemetry_export_interval_millis)
        tracer_provider.add_span_processor(
            self._processor
        )

        # Set as global provider
        self._provider = tracer_provider
        try:
            trace.set_tracer_provider(tracer_provider)
        except Exception:
            self.logger.warning(f"The tracer provider was previously set, and will take precidence over the set in this package: anaconda_opentelemetry.")

        # Get tracer for this service
        return trace.get_tracer(self.service_name, self.service_version)

    def get_span(self, name: str, attributes: AttrDict = {}, carrier: Dict[str,str] = None) -> trace.Span:
        # Extract context if applicable
        if carrier is None:
            context = None
        else:
            context = get_global_textmap().extract(carrier)

        span = self.tracer.start_span(name, context=context, attributes=attributes)

        # Inject context if applicable
        if carrier is not None:
            context = trace.set_span_in_context(span, context)
            get_global_textmap().inject(carrier, context=context)

        return _ASpan(name, span, attributes=attributes)
