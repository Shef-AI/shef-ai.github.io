# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append("./")

import pytest, threading
from unittest.mock import Mock, MagicMock, patch, call
from enum import Enum

from anaconda_opentelemetry.exporter_shim import (
    ExporterState,
    _OTLPExporterMixin,
    OTLPMetricExporterShim,
    OTLPSpanExporterShim,
    OTLPLogExporterShim
)

class MockExporter:
    """Mock exporter class for testing"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.exported_items = []
        self.is_shutdown = False
        self.is_flushed = False
        
    def export(self, items):
        self.exported_items.append(items)
        return "SUCCESS"
    
    def shutdown(self):
        self.is_shutdown = True
        return True
    
    def force_flush(self, timeout=None):
        self.is_flushed = True
        return True


class MockMetricExporter(MockExporter):
    """Mock metric exporter with temporality and aggregation properties"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._preferred_temporality = "CUMULATIVE"
        self._preferred_aggregation = "SUM"


class TestExporterState:
    def test_exporter_state_enum_values(self):
        assert ExporterState.READY.value == 1
        assert ExporterState.UPDATING.value == 2
        
    def test_exporter_state_enum_members(self):
        assert hasattr(ExporterState, 'READY')
        assert hasattr(ExporterState, 'UPDATING')
        assert len(ExporterState) == 2


class TestOTLPExporterMixin:
    def test_initialization(self):
        mixin = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        
        assert mixin._exporter_class == MockExporter
        assert mixin._init_kwargs == {"endpoint": "http://localhost:4317"}
        assert isinstance(mixin._exporter, MockExporter)
        assert mixin._state == ExporterState.READY
        assert type(mixin._lock).__name__ == 'lock'
        
    def test_initialization_with_multiple_kwargs(self):
        kwargs = {
            "endpoint": "http://localhost:4317",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        }
        mixin = _OTLPExporterMixin(MockExporter, **kwargs)
        
        assert mixin._init_kwargs == kwargs
        assert mixin._exporter.kwargs == kwargs
        
    def test_export_delegates_to_exporter(self):
        mixin = _OTLPExporterMixin(MockExporter)
        items = ["item1", "item2"]
        
        result = mixin.export(items)
        
        assert result == "SUCCESS"
        assert mixin._exporter.exported_items == [items]
        
    def test_shutdown_delegates_to_exporter(self):
        mixin = _OTLPExporterMixin(MockExporter)
        
        result = mixin.shutdown()
        
        assert result == True
        assert mixin._exporter.is_shutdown == True
               
    def test_change_signal_endpoint_successful(self):
        mixin = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        mixin._signal = "metrics"
        
        config = Mock()
        config._change_signal_endpoint.return_value = "http://newhost:8080/v1/metrics"
        
        batch_access = Mock()
        
        result = mixin.change_signal_endpoint(
            batch_access,
            config,
            "http://newhost:8080",
            auth_token="token123"
        )
        
        assert result == True
        assert mixin._init_kwargs['endpoint'] == "http://newhost:8080/v1/metrics"
        assert mixin._state == ExporterState.READY
        
        config._change_signal_endpoint.assert_called_once_with(
            "metrics",
            "http://newhost:8080",
            auth_token="token123"
        )
        
        batch_access.force_flush.assert_called_once()
        
        assert isinstance(mixin._exporter, MockExporter)
        assert mixin._exporter.kwargs['endpoint'] == "http://newhost:8080/v1/metrics"
               
    def test_change_signal_endpoint_handles_exporter_creation_failure(self):
        class FailingExporter:
            def __init__(self, **kwargs):
                if kwargs.get('endpoint') == "http://invalid:8080/v1/metrics":
                    raise ValueError("Invalid endpoint")
                self.kwargs = kwargs
                self.is_shutdown = False
                
            def shutdown(self):
                self.is_shutdown = True
                
        mixin = _OTLPExporterMixin(FailingExporter, endpoint="http://localhost:4317")
        mixin._signal = "metrics"
        old_exporter = mixin._exporter
        
        config = Mock()
        config._change_signal_endpoint.return_value = "http://invalid:8080/v1/metrics"
        
        batch_access = Mock()
        
        result = mixin.change_signal_endpoint(
            batch_access,
            config,
            "http://invalid:8080"
        )
        
        assert result == False
        assert mixin._state == ExporterState.READY
        assert mixin._exporter is old_exporter
        batch_access.force_flush.assert_not_called()
        
    def test_change_signal_endpoint_thread_safety(self):
        """Test that change_signal_endpoint properly locks during state changes"""
        mixin = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        mixin._signal = "metrics"
        
        config = Mock()
        config._change_signal_endpoint.return_value = "http://newhost:8080/v1/metrics"
        
        batch_access = Mock()
        
        original_lock = mixin._lock
        mock_lock = MagicMock()
        
        states_observed = []
        enter_count = [0]
        def track_state_on_enter(*args):
            enter_count[0] += 1
            states_observed.append(mixin._state)
            return original_lock.__enter__()
        
        def track_state_on_exit(*args):
            states_observed.append(mixin._state)
            return original_lock.__exit__(*args)
            
        mock_lock.__enter__ = Mock(side_effect=track_state_on_enter)
        mock_lock.__exit__ = Mock(side_effect=track_state_on_exit)
        mock_lock.acquire = original_lock.acquire
        mock_lock.release = original_lock.release
        
        mixin._lock = mock_lock
        
        mixin.change_signal_endpoint(batch_access, config, "http://newhost:8080")
        
        # Should acquire lock at least twice
        assert enter_count[0] >= 2
        assert mock_lock.__enter__.call_count == mock_lock.__exit__.call_count
        # Check that UPDATING and READY were both active states at one point
        assert ExporterState.UPDATING in states_observed
        assert mixin._state == ExporterState.READY


class TestOTLPMetricExporterShim:        
    def test_initialization(self):
        shim = OTLPMetricExporterShim(MockMetricExporter, endpoint="http://localhost:4317")
        
        assert isinstance(shim._exporter, MockMetricExporter)
        assert shim._signal == 'metrics'
        
    def test_properties_follow_exporter_changes(self):
        shim = OTLPMetricExporterShim(MockMetricExporter)
        
        shim._exporter._preferred_temporality = "DELTA"
        shim._exporter._preferred_aggregation = "HISTOGRAM"
        
        assert shim._preferred_temporality == "DELTA"
        assert shim._preferred_aggregation == "HISTOGRAM"
        
    def test_composition_of_metric_exporter(self):
        from opentelemetry.sdk.metrics.export import MetricExporter
        
        shim = OTLPMetricExporterShim(MockMetricExporter)
        assert isinstance(shim, MetricExporter)
        
    def test_export_with_metrics(self):
        shim = OTLPMetricExporterShim(MockMetricExporter)
        
        metrics = [{"name": "cpu_usage", "value": 75.5}]
        result = shim.export(metrics)
        
        assert result == "SUCCESS"
        assert shim._exporter.exported_items == [metrics]


class TestOTLPSpanExporterShim:        
    def test_initialization(self):
        shim = OTLPSpanExporterShim(MockExporter, endpoint="http://localhost:4317")
        
        assert isinstance(shim._exporter, MockExporter)
        assert shim._signal == 'tracing'
        
    def test_inherits_from_span_exporter(self):
        from opentelemetry.sdk.trace.export import SpanExporter
        
        shim = OTLPSpanExporterShim(MockExporter)
        assert isinstance(shim, SpanExporter)
        
    def test_export_with_spans(self):
        shim = OTLPSpanExporterShim(MockExporter)
        
        spans = [{"trace_id": "123", "span_id": "456"}]
        result = shim.export(spans)
        
        assert result == "SUCCESS"
        assert shim._exporter.exported_items == [spans]
        
    def test_change_signal_endpoint_uses_tracing_signal(self):
        shim = OTLPSpanExporterShim(MockExporter)
        
        config = Mock()
        config._change_signal_endpoint.return_value = "http://newhost:8080/v1/traces"
        
        batch_access = Mock()
        
        shim.change_signal_endpoint(batch_access, config, "http://newhost:8080")
        
        config._change_signal_endpoint.assert_called_once_with(
            "tracing",
            "http://newhost:8080",
            auth_token=None
        )


class TestOTLPLogExporterShim:       
    def test_initialization(self):
        shim = OTLPLogExporterShim(MockExporter, endpoint="http://localhost:4317")
        
        assert isinstance(shim._exporter, MockExporter)
        assert shim._signal == 'logging'
        
    def test_inherits_from_log_exporter(self):
        from anaconda_opentelemetry._compat import LogRecordExporter

        shim = OTLPLogExporterShim(MockExporter)
        assert isinstance(shim, LogRecordExporter)
        
    def test_export_with_logs(self):
        shim = OTLPLogExporterShim(MockExporter)
        
        logs = [{"level": "INFO", "message": "Test log"}]
        result = shim.export(logs)
        
        assert result == "SUCCESS"
        assert shim._exporter.exported_items == [logs]
        
    def test_change_signal_endpoint_uses_logging_signal(self):
        shim = OTLPLogExporterShim(MockExporter)
        
        config = Mock()
        config._change_signal_endpoint.return_value = "http://newhost:8080/v1/logs"
        
        batch_access = Mock()
        
        shim.change_signal_endpoint(batch_access, config, "http://newhost:8080")
        
        config._change_signal_endpoint.assert_called_once_with(
            "logging",
            "http://newhost:8080",
            auth_token=None
        )

class TestMockExport:
    def test_multiple_exporters_can_coexist(self):
        """Test that multiple shim instances don't interfere with each other"""
        metric_shim = OTLPMetricExporterShim(MockMetricExporter, endpoint="http://metrics:4317")
        span_shim = OTLPSpanExporterShim(MockExporter, endpoint="http://traces:4317")
        log_shim = OTLPLogExporterShim(MockExporter, endpoint="http://logs:4317")
        
        assert metric_shim._init_kwargs['endpoint'] == "http://metrics:4317"
        assert span_shim._init_kwargs['endpoint'] == "http://traces:4317"
        assert log_shim._init_kwargs['endpoint'] == "http://logs:4317"
        
        metric_shim.export([{"metric": "data"}])
        span_shim.export([{"span": "data"}])
        log_shim.export([{"log": "data"}])
        
        assert len(metric_shim._exporter.exported_items) == 1
        assert len(span_shim._exporter.exported_items) == 1
        assert len(log_shim._exporter.exported_items) == 1
        
    def test_endpoint_update_sequence(self):
        """Test a sequence of endpoint updates"""
        shim = OTLPMetricExporterShim(MockMetricExporter, endpoint="http://localhost:4317")
        
        config = Mock()
        batch_access = Mock()
        
        endpoints = [
            "http://host1:8080",
            "http://host2:9090",
            "http://host3:7070"
        ]
        
        for endpoint in endpoints:
            config._change_signal_endpoint.return_value = f"{endpoint}/v1/metrics"
            result = shim.change_signal_endpoint(batch_access, config, endpoint)
            
            assert result == True
            assert shim._init_kwargs['endpoint'] == f"{endpoint}/v1/metrics"
            assert shim._state == ExporterState.READY
            
        assert batch_access.force_flush.call_count == len(endpoints)
        
    def test_concurrent_export_and_update(self):
        """Test that export works correctly during endpoint updates"""
        import time
        from threading import Thread
        
        shim = OTLPMetricExporterShim(MockMetricExporter, endpoint="http://localhost:4317")
        
        export_results = []
        update_results = []
        
        def export_continuously():
            for i in range(5):
                try:
                    result = shim.export([{"item": i}])
                    export_results.append(result)
                except Exception as e:
                    export_results.append(f"error: {e}")
                time.sleep(0.01)
                
        def change_signal_endpoint():
            config = Mock()
            config._change_signal_endpoint.return_value = "http://newhost:8080/v1/metrics"
            batch_access = Mock()
            
            time.sleep(0.05)
            result = shim.change_signal_endpoint(batch_access, config, "http://newhost:8080")
            update_results.append(result)
            
        export_thread = Thread(target=export_continuously)
        update_thread = Thread(target=change_signal_endpoint)
        
        export_thread.start()
        update_thread.start()
        
        export_thread.join()
        update_thread.join()
        
        assert all(r == "SUCCESS" for r in export_results)
        assert len(export_results) == 5
        
        assert update_results[0] == True

    def test_export_handles_exception(self):
        """Test that export catches and logs exceptions, returning False"""
        shim = OTLPMetricExporterShim(MockMetricExporter, endpoint="http://localhost:4317")

        shim._exporter = MagicMock()
        shim._exporter.export.side_effect = ConnectionError("Connection refused")

        shim._logger = MagicMock()

        result = shim.export([{"test": "data"}])

        assert result == False
        shim._logger.error.assert_called_once_with("Failed to export: Connection refused")


class TestSwapExporter:
    def test_swap_exporter_replaces_exporter(self):
        shim = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        old_exporter = shim._exporter

        result = shim._swap_exporter()

        assert result == True
        assert shim._exporter is not old_exporter
        assert old_exporter.is_shutdown == True

    def test_swap_exporter_with_batch_access_flushes(self):
        shim = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        batch_access = Mock()

        shim._swap_exporter(batch_access=batch_access)

        batch_access.force_flush.assert_called_once()

    def test_swap_exporter_without_batch_access_skips_flush(self):
        shim = _OTLPExporterMixin(MockExporter, endpoint="http://localhost:4317")
        old_exporter = shim._exporter

        shim._swap_exporter()

        assert old_exporter.is_shutdown == True

    def test_swap_exporter_failure_keeps_old_exporter(self):
        class FailOnSecondCreate:
            _count = 0
            def __init__(self, **kwargs):
                FailOnSecondCreate._count += 1
                if FailOnSecondCreate._count > 1:
                    raise RuntimeError("fail")
                self.kwargs = kwargs
                self.is_shutdown = False
            def shutdown(self):
                self.is_shutdown = True

        shim = _OTLPExporterMixin(FailOnSecondCreate, endpoint="http://localhost:4317")
        old_exporter = shim._exporter

        result = shim._swap_exporter()

        assert result == False
        assert shim._exporter is old_exporter
        assert old_exporter.is_shutdown == False


