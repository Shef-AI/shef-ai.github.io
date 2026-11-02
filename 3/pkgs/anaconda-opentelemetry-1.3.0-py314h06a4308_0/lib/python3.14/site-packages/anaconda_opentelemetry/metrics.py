# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# metrics.py
"""
Anaconda Telemetry - Metrics signal class.
"""

import re
from typing import Dict, Any

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Counter, UpDownCounter, Histogram, ObservableCounter, ObservableUpDownCounter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter, AggregationTemporality

from ._compat import GaugeInstrument

from .common import _AnacondaCommon, MetricsNotInitialized
from .config import Configuration as Config
from .attributes import ResourceAttributes as Attributes
from .exporter_shim import OTLPMetricExporterShim
from .formatting import AttrDict


class _AnacondaMetrics(_AnacondaCommon):
    # Singleton instance (internal only); provide a single instance of the metrics class
    _instance = None

    _default_temporality: dict[type,AggregationTemporality] = {
        Counter: AggregationTemporality.DELTA,
        ObservableCounter: AggregationTemporality.DELTA,
        Histogram: AggregationTemporality.CUMULATIVE,
        UpDownCounter: AggregationTemporality.DELTA,
        ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
        GaugeInstrument: AggregationTemporality.CUMULATIVE,  # A gauge is a last-value metric; DELTA is meaningless for it.
    }

    _cumulative_temporality: dict[type,AggregationTemporality] = {
        Counter: AggregationTemporality.CUMULATIVE,
        ObservableCounter: AggregationTemporality.CUMULATIVE,
        Histogram: AggregationTemporality.CUMULATIVE,
        UpDownCounter: AggregationTemporality.CUMULATIVE,
        ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
        GaugeInstrument: AggregationTemporality.CUMULATIVE,
    }

    _temporalityValue: dict[bool,str] = {
        False: "DELTA",
        True: "CUMULATIVE"
    }

    def __init__(self, config: Config, attributes: Attributes):
        super().__init__(config, attributes)

        self.metrics_endpoint = config._get_metrics_endpoint()
        self.telemetry_export_interval_millis = config._get_metrics_export_interval_ms()
        self.counter_objects: Dict[str, Any] = {}
        self.up_down_counter_objects: Dict[str, Any] = {}
        self.histogram_objects: Dict[str, Any] = {}
        self.gauge_objects: Dict[str, Any] = {}

        self.meter = self._setup_metrics(config)
        self.create_dispatcher = {
            'simple_counter': self.meter.create_counter,
            'simple_up_down_counter': self.meter.create_up_down_counter,
            'histogram': self.meter.create_histogram,
            'gauge': self.meter.create_gauge
        }
        self.type_list = {
            'simple_counter': self.counter_objects,
            'simple_up_down_counter': self.up_down_counter_objects,
            'histogram': self.histogram_objects,
            'gauge': self.gauge_objects
        }

    def _setup_metrics(self, config: Config) -> metrics.Meter:
        if self.use_console_exporters:
            exporter = ConsoleMetricExporter(preferred_temporality=self._get_temporality())
        else:
            auth_token = config._get_auth_token_metrics()
            headers: Dict[str, str] = {}
            if auth_token is not None:
                headers['authorization'] = f'Bearer {auth_token}'
            if config._get_request_protocol_metrics() in ['grpc', 'grpcs']:  # gRPC
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPMetricExportergRPC
                insecure = not config._get_TLS_metrics()
                exporter = OTLPMetricExporterShim(
                    OTLPMetricExportergRPC,
                    endpoint=self.metrics_endpoint,
                    insecure=insecure,
                    credentials=config._get_ca_cert_metrics() if not insecure else None,
                    headers=headers,
                    preferred_temporality=self._get_temporality()
                )
            else:  # HTTP
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPMetricExporterHTTP
                http_kwargs = self._build_http_exporter_kwargs(
                    'metrics', self.metrics_endpoint, headers,
                    preferred_temporality=self._get_temporality()
                )
                exporter = OTLPMetricExporterShim(
                    OTLPMetricExporterHTTP,
                    **http_kwargs
                )

        self.exporter = exporter
        self.metric_reader = PeriodicExportingMetricReader(self.exporter, export_interval_millis=self.telemetry_export_interval_millis)
        # Create and set meter provider
        meter_provider = MeterProvider(
            resource=self.resource,
            metric_readers=[self.metric_reader],
            shutdown_on_exit=self._shutdown_on_exit
        )
        self._provider = meter_provider
        try:
            metrics.set_meter_provider(meter_provider)
        except Exception as e:
            self.logger.warning(f"The metrics provider was previously set and will take precidence over this call.")
        # Get meter for this service
        return metrics.get_meter(self.service_name, self.service_version)

    def _get_temporality(self) -> dict[type,AggregationTemporality]:
        if self._config._get_use_cumulative_metrics() == True:
            return _AnacondaMetrics._cumulative_temporality
        return _AnacondaMetrics._default_temporality

    def _check_for_metric(self, metric_name: str, metric_type: str) -> bool:
        bucket_list = self.type_list.get(metric_type, None)
        if bucket_list is None:
            return False
        return bucket_list.get(metric_name, None) is not None

    def _get_or_create_metric(self, metric_name: str, metric_type: str = 'simple_up_down_counter', units: str = '#', description='No description.') -> Any:
        bucket_list = self.type_list.get(metric_type, None)
        if bucket_list is None:
            raise MetricsNotInitialized(f"Metric type '{metric_type}' is unknown!")
        metric = bucket_list.get(metric_name, None)
        if metric is None:
            if not re.fullmatch(r"^[A-Za-z][A-Za-z_0-9.]*[A-Za-z_0-9]$", metric_name):
                self.logger.warning(f"Metric {metric_name} does not match valid regex: r\"^[A-Za-z][A-Za-z_0-9.]*[A-Za-z_0-9]$\"")
                return None
            create = self.create_dispatcher.get(metric_type, None)
            if create is None:
                self.logger.warning(f"Metric '{metric_name}' has an invalid type '{metric_type}'; cannot create metric.")
                return None
            metric = create(
                metric_name,
                unit=units,
                description=description
            )
            if metric is None:
                self.logger.error(f"Failed to create metric '{metric_name}'!")
            bucket_list[metric_name] = metric
        return metric

    def record_histogram(self, metric_name, value, attributes: AttrDict={}) -> bool:
        # Record a histogram metric with the given name and value.
        metric = self._get_or_create_metric(metric_name, metric_type='histogram', units='#', description='Dynamically create histogram metric.')
        if metric is None:
            self.logger.error(f"Metric '{metric_name}' failed to be created.")
            return False
        metric.record(value, attributes)
        return True

    def set_gauge(self, metric_name, value, attributes: AttrDict={}) -> bool:
        # Set a gauge metric with the given name to the given value; the last value set wins.
        # Unlike the other instruments, OTel's Gauge.set() does no arithmetic on the value, so a
        # non-numeric value is accepted here and only fails later during serialization -- which
        # discards the whole export batch, not just this metric. Reject it up front instead.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.logger.error(f"Metric '{metric_name}' gauge value must be an int or float, not {type(value).__name__}.")
            return False
        metric = self._get_or_create_metric(metric_name, metric_type='gauge', units='#', description='Dynamically create gauge metric.')
        if metric is None:
            self.logger.error(f"Metric '{metric_name}' failed to be created.")
            return False
        metric.set(value, attributes)
        return True

    def increment_counter(self, counter_name, by=1, attributes: AttrDict={}) -> bool:
        # Increment a counter with the given name by the 'by' parameter. abs(by) is used.
        metric = None
        if self._check_for_metric(metric_name=counter_name, metric_type='simple_counter'):
            metric = self._get_or_create_metric(counter_name, metric_type='simple_counter')
        if metric is None:
            metric = self._get_or_create_metric(counter_name, metric_type='simple_up_down_counter')
        if metric is None:
            self.logger.error(f"Metric '{counter_name}' failed to be created.")
            return False
        metric.add(abs(by), attributes)
        return True

    def decrement_counter(self, counter_name, by=1, attributes:AttrDict={}) -> bool:
        # Decrement a up down counter with the given name by the 'by' parameter. abs(by) is used.
        metric = self._get_or_create_metric(counter_name)
        if metric is None:
            self.logger.error(f"Metric '{counter_name}' failed to be created.")
            return False
        metric.add(-abs(by), attributes)
        return True
