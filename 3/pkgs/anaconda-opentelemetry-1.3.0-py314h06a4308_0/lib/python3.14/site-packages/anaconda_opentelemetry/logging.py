# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# logging.py
"""
Anaconda Telemetry - Logging signal class and EventLogger.
"""

import json
import logging
from typing import Dict

from ._compat import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    LoggerProvider,
    LoggingHandler,
    get_logger_provider,
    set_logger_provider,
)
from .common import _AnacondaCommon
from .config import Configuration as Config
from .attributes import ResourceAttributes as Attributes
from .exporter_shim import OTLPLogExporterShim
from .formatting import AttrDict, EventPayload, log_event_name_key


class EventLogger:
    """
    Emits log records purely as OTel log telemetry, bypassing Python's
    logging hierarchy so they never appear in console/file handlers or
    interfere with developer log levels. Should be used if the logs
    being collected are not developer logs, and correspond to events.
    """

    def __init__(
        self,
        provider: LoggerProvider,
        logger_name: str = "event_logger",
    ):
        self._logger = provider.get_logger(logger_name)

    def _send_event(
        self,
        body: EventPayload,
        event_name: str,
        attributes: AttrDict={},
    ):
        if not isinstance(body, str):
            body = json.dumps(body)
        # update attributes with event name - mandatory for event logs
        # copy first: `attributes` may be a caller-owned dict (or the default {})
        attributes = {**attributes, log_event_name_key: event_name}
        self._logger.emit(body=body, attributes=attributes)


class _AnacondaLogger(_AnacondaCommon):
    # Singleton instance (internal only); provide a logger handler for OpenTelemetry log instrumentation
    _instance = None

    _default_log_attributes = {log_event_name_key: "__LOG__"}

    def __init__(self, config: Config, attributes: Attributes):
        super().__init__(config, attributes)
        self.log_level = self._get_log_level(config._get_logging_level())
        self.logger_endpoint = config._get_logging_endpoint()

        # send_event and get_telemetry_logger_handler emit through self._provider, not the
        # global one. set_logger_provider ignores a second caller instead of raising, so
        # check identity to detect that another library got there first.
        self._provider = LoggerProvider(resource=self.resource, shutdown_on_exit=self._shutdown_on_exit)
        set_logger_provider(self._provider)
        if get_logger_provider() is not self._provider:
            logging.getLogger(__package__).debug(
                "A global OTel LoggerProvider was already set by another library; "
                "anaconda_opentelemetry keeps using its own provider for log telemetry."
            )
        self._console_exporter: ConsoleLogRecordExporter | None = None
        # Add OTLP exporter
        if self.use_console_exporters:
            exporter = ConsoleLogRecordExporter()
            self._console_exporter = exporter
        else:
            auth_token = config._get_auth_token_logging()
            headers: Dict[str, str] = {}
            if auth_token is not None:
                headers['authorization'] = f'Bearer {auth_token}'
            if config._get_request_protocol_logging() in ['grpc', 'grpcs']:  # gRPC
                from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as OTLPLogExportergRPC
                insecure = not config._get_TLS_logging()
                exporter = OTLPLogExporterShim(
                    OTLPLogExportergRPC,
                    endpoint=self.logger_endpoint,
                    insecure=insecure,
                    credentials=config._get_ca_cert_logging() if not insecure else None,
                    headers=headers
                )
            else:  # HTTP
                from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as OTLPLogExporterHTTP
                http_kwargs = self._build_http_exporter_kwargs('logging', self.logger_endpoint, headers)
                exporter = OTLPLogExporterShim(
                    OTLPLogExporterHTTP,
                    **http_kwargs
                )

        self.exporter = exporter
        self._processor = BatchLogRecordProcessor(self.exporter)
        self._provider.add_log_record_processor(self._processor)

    def _get_log_handler(self) -> LoggingHandler:
        handler = LoggingHandler(level=self.log_level, logger_provider=self._provider)
        handler.addFilter(self._set_default_attribute_filter())
        return handler

    def _set_default_attribute_filter(self) -> logging.Filter:
        attrs = self._default_log_attributes
        f = logging.Filter()
        def _filter(record):
            for k, v in attrs.items():
                if not hasattr(record, k):
                    setattr(record, k, v)
            return True
        f.filter = _filter
        return f

    def _get_event_logger(self, logger_name: str = None) -> EventLogger:
        if logger_name is None:
            logger_name = f'{self.service_name}_event_logger'
        return EventLogger(self._provider, logger_name=logger_name)

    def _get_log_level(self, str_level: str)-> int:
        # Convert string from config file to logging level.
        levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "warn": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "fatal": logging.CRITICAL
        }
        return levels.get(str_level.lower(), logging.DEBUG)

    def _test_set_console_mock(self, new_out):  # For testing only...
        if self._console_exporter is not None and new_out is not None:
            saved = self._console_exporter.out
            self._console_exporter.out = new_out
            return saved
        return None
