# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append("./")

import logging
import os
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from anaconda_opentelemetry.config import Configuration as Config
from anaconda_opentelemetry.signals import _suppress_otel_export_errors

class TestVerboseExportErrors:
    def test_verbose_export_errors_default_false(self):
        cfg = Config(default_endpoint="http://localhost:4317")
        assert cfg._get_verbose_export_errors() == False

    def test_suppress_otel_export_errors_silences_logs(self):
        _suppress_otel_export_errors()

        otel_loggers = [
            'opentelemetry.exporter.otlp.proto.grpc.exporter',
            'opentelemetry.exporter.otlp.proto.http.exporter',
            'opentelemetry.exporter.otlp.proto.grpc.metric_exporter',
            'opentelemetry.exporter.otlp.proto.http.metric_exporter',
            'opentelemetry.exporter.otlp.proto.grpc.trace_exporter',
            'opentelemetry.exporter.otlp.proto.http.trace_exporter',
            'opentelemetry.exporter.otlp.proto.grpc._log_exporter',
            'opentelemetry.exporter.otlp.proto.http._log_exporter',
        ]

        for logger_name in otel_loggers:
            logger = logging.getLogger(logger_name)
            assert logger.getEffectiveLevel() == logging.CRITICAL
            assert not logger.isEnabledFor(logging.WARNING)
            assert not logger.isEnabledFor(logging.ERROR)

    def test_suppress_otel_export_errors_overrides_preexisting_child_level(self):
        child = logging.getLogger('opentelemetry.sdk.trace.export')
        child.setLevel(logging.DEBUG)

        _suppress_otel_export_errors()

        assert child.level == logging.NOTSET
        assert not child.isEnabledFor(logging.ERROR)

    # the two tests below exercise the gate in signals.py that decides whether suppression is
    # applied at all, so they must run in a clean interpreter: under pytest the root logger
    # already carries handlers, which hides whether a real user would see the output
    closed_endpoint = 'http://127.0.0.1:45999'  # nothing listening, so every export fails
    transient_error = "Transient error"

    def _run(self, verbose: bool) -> subprocess.CompletedProcess:
        # a short export interval plus shutdown_on_exit=False keeps this fast: the first failed
        # export logs immediately, so there is no need to sit through the exporter's retry backoff
        snippet = (
            'import time\n'
            'from anaconda_opentelemetry import initialize_telemetry, increment_counter\n'
            'from anaconda_opentelemetry.config import Configuration\n'
            'from anaconda_opentelemetry.attributes import ResourceAttributes\n'
            f"cfg = Configuration(default_endpoint='{self.closed_endpoint}')\n"
            'cfg.set_skip_internet_check(True)\n'
            'cfg.set_metrics_export_interval_ms(100)\n'
            'cfg.set_shutdown_on_exit(False)\n'
            f'cfg.set_verbose_export_errors({verbose})\n'
            "initialize_telemetry(cfg, ResourceAttributes(service_name='test', service_version='1.0.0'))\n"
            "increment_counter('test_metric', by=1)\n"
            'time.sleep(1.0)\n'
        )
        # strip ATEL_ vars so a developer's environment cannot override the flag under test
        env = {k: v for k, v in os.environ.items() if not k.startswith('ATEL_')}
        return subprocess.run([sys.executable, '-c', snippet], capture_output=True, text=True, timeout=60, env=env)

    def test_export_errors_print_when_verbose_enabled(self):
        result = self._run(True)
        assert self.transient_error in result.stderr

    def test_export_errors_silenced_when_verbose_disabled(self):
        result = self._run(False)
        assert result.stdout == ""
        assert result.stderr == ""
