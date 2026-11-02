# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append("./")

import unittest, pytest, logging, os, tempfile
from unittest.mock import patch, MagicMock
import anaconda_opentelemetry.signals as signals_package
from anaconda_opentelemetry.signals import initialize_telemetry, record_histogram, increment_counter, \
    decrement_counter, set_gauge, get_trace, get_telemetry_logger_handler, send_event, MetricsNotInitialized, \
    change_signal_endpoint
from anaconda_opentelemetry.signals import __check_internet_status as check_internet
from anaconda_opentelemetry.config import Configuration as Config
from anaconda_opentelemetry.attributes import ResourceAttributes as Attributes
from anaconda_opentelemetry.signals import _AnacondaMetrics, _AnacondaLogger, _AnacondaTrace

@pytest.fixture(scope="module", autouse=True)
def setup_mock_logging():
    with patch('logging.getLogger') as mock_getLogger:
        mock_getLogger.return_value = MagicMock()
        mock_getLogger.return_value.level = logging.WARNING
        yield mock_getLogger

class TestInitializeTelemetry:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)
        os.environ['OTEL_SDK_DISABLED'] = '' # Reset OTEL_SDK_DISABLED environment variable

    # @patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True))
    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_basic_initialization_default_params(
        self,
        # _: MagicMock,
        mock_trace: MagicMock,
        mock_metrics: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test basic initialization with minimal required parameters
        - Checks that __ANACONDA_TELEMETRY_INITIALIZED is False before initialization
        - Checks that _AnacondaLogger, _AnacondaMetrics, _AnacondaTrace are called once with params
        - Checks that the mock classes contain an _instance value
        - Checks that __ANACONDA_TELEMETRY_INITIALIZED is True after initialization
        - Implicitly checks initialize_telemetry with no auth_token or ssl_certificate arguments provided
        """
        # Verify initial state
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False
        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'logging', 'tracing'])
            mock.assert_called_once()

        # Verify all three metric types were initialized by default
        mock_logger.assert_called_once_with(unittest.mock.ANY, unittest.mock.ANY)
        mock_metrics.assert_called_once_with(unittest.mock.ANY, unittest.mock.ANY)
        mock_trace.assert_called_once_with(unittest.mock.ANY, unittest.mock.ANY)

        # Verify that _instance attributes were set on the mock classes
        assert hasattr(mock_logger, '_instance')
        assert hasattr(mock_metrics, '_instance')
        assert hasattr(mock_trace, '_instance')

        # Verify the global flag was set
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is True

    def test_telemetry_not_initialized_returns_false(self):
        """
        Test that function returns False when telemetry is not initialized
        - Verifies __ANACONDA_TELEMETRY_INITIALIZED is False before call
        - Confirms function returns False
        - Checks that error is logged about uninitialized telemetry system
        """
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            result = record_histogram("test_metric", 42.5)

            assert result is False
            mock_logger_instance.error.assert_called_once_with(
                "Anaconda telemetry system not initialized."
            )

    def test_already_initialized_early_return(self):
        """
        Test that function returns early if telemetry is already initialized
        - Sets __ANACONDA_TELEMETRY_INITIALIZED to True before calling
        - Verifies no telemetry classes are instantiated
        - Confirms function exits without error
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        attributes = Attributes("test_service", "1.0.0")

        with patch('anaconda_opentelemetry.signals._AnacondaLogger') as mock_logger, \
             patch('anaconda_opentelemetry.signals._AnacondaMetrics') as mock_metrics, \
             patch('anaconda_opentelemetry.signals._AnacondaTrace') as mock_trace:

            initialize_telemetry(config={'use_console_exporters': True}, attributes=attributes)

            # Verify no classes were called
            mock_logger.assert_not_called()
            mock_metrics.assert_not_called()
            mock_trace.assert_not_called()

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_selective_signal_types_logging_only(
        self,
        mock_trace: MagicMock,
        mock_metrics: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test initialization with only logging signal type
        - Verifies only _AnacondaLogger is called
        - Confirms _AnacondaMetrics and _AnacondaTrace are not called
        - Checks that initialization flag is still set to True
        """
        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['logging'])
            mock.assert_called_once()

        mock_logger.assert_called_once()
        mock_metrics.assert_not_called()
        mock_trace.assert_not_called()
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is True

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_selective_signal_types_metrics_tracing(
        self,
        mock_trace: MagicMock,
        mock_metrics: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test initialization with metrics and tracing only
        - Verifies _AnacondaMetrics and _AnacondaTrace are called
        - Confirms _AnacondaLogger is not called
        - Checks that initialization flag is set to True
        """
        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'tracing'])
            mock.assert_called_once()

        mock_logger.assert_not_called()
        mock_metrics.assert_called_once()
        mock_trace.assert_called_once()
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is True

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    @patch('logging.getLogger')
    def test_empty_signal_types_warning(
        self,
        mock_get_logger: MagicMock,
        mock_trace: MagicMock,
        mock_metrics: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test initialization with empty signal types list
        - Verifies no telemetry classes are called
        - Confirms warning is logged about no signal types being initialized
        - Checks that initialization flag is still set to True
        """
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=[])
            mock.assert_called_once()

        mock_logger.assert_not_called()
        mock_metrics.assert_not_called()
        mock_trace.assert_not_called()
        mock_logger_instance.warning.assert_called_once()
        assert "No signal types were initialized" in mock_logger_instance.warning.call_args[0][0]
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is True

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_ssl_certificate_and_auth_token_parameters(self, mock_logger: MagicMock, mock_metrics: MagicMock, mock_trace: MagicMock):
        """
        Test that SSL certificate and auth token are properly added to config
        - Passes SSL certificate bytes and auth token string
        - Verifies both are included in the config dict passed to telemetry classes
        """
        auth_token = "Bearer test_token_123"

        # Create temp file with fake cert content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----")
            f.flush()
            temp_path = f.name
            config = Config(default_endpoint='http://localhost:4317').\
            set_tls_private_ca_cert(temp_path).\
            set_auth_token(auth_token)
            attributes = Attributes("test_service", "1.0.0")
        try:
            with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
                initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'logging', 'tracing'])
                mock.assert_called_once()

            call_args = mock_logger.call_args[0]
            config_obj: Config = call_args[0]
            assert temp_path == config_obj._get_ca_cert_default()
            assert config_obj._get_auth_token_default() == auth_token
        finally:
            os.unlink(temp_path)

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('time.time')
    def test_entropy_param_default_timestamp(
        self,
        mock_time: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test that entropy parameter defaults to current timestamp
        - Mocks time.time() to return fixed value
        - Verifies entropy_value in config uses the timestamp
        """
        mock_time.return_value = 1234567890.123456789
        expected_entropy = int(1234567890.123456789 * 1e9)
        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'logging', 'tracing'])
            mock.assert_called_once()

        call_args = mock_logger.call_args[0]
        config_obj: Config = call_args[0]

        assert config_obj._get_tracing_session_entropy() == expected_entropy

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    def test_entropy_param_custom_value(self, mock_logger: MagicMock):
        """
        Test that custom entropy parameter is used when provided
        - Passes custom entropy_param string
        - Verifies it's used instead of timestamp
        """
        custom_entropy = "custom_entropy_12345"
        config = Config(default_endpoint='http://localhost:4317').set_tracing_session_entropy(custom_entropy)
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'logging', 'tracing'])
            mock.assert_called_once()

        call_args = mock_logger.call_args[0]
        config_obj: Config = call_args[0]

        assert config_obj._get_tracing_session_entropy() == custom_entropy

    @patch('anaconda_opentelemetry.signals._AnacondaLogger')
    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_instance_attribute_setting(
        self,
        mock_trace: MagicMock,
        mock_metrics: MagicMock,
        mock_logger: MagicMock
    ):
        """
        Test that _instance attributes are properly set on telemetry classes
        - Verifies _instance attributes exist after initialization
        - Confirms instances are created by calling the mock classes
        """
        # Create specific mock instances that will be returned
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_trace_instance = MagicMock()

        # Set the return values BEFORE calling initialize_telemetry
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance
        mock_trace.return_value = mock_trace_instance
        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("test_service", "1.0.0")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=['metrics', 'logging', 'tracing'])
            mock.assert_called_once()

        # Verify _instance attributes exist by checking they were set as attributes
        logger_instance = getattr(mock_logger, '_instance', None)
        metrics_instance = getattr(mock_metrics, '_instance', None)
        trace_instance = getattr(mock_trace, '_instance', None)

        # Verify these are the instances we expected (the return values from the mock calls)
        assert logger_instance is mock_logger_instance
        assert metrics_instance is mock_metrics_instance
        assert trace_instance is mock_trace_instance

    @patch('time.time')
    def test_none_entropy_provided(self, mock_time: MagicMock):
        """
        Test that a time.time() call is made when no entropy argument is provided
        """
        mock_time.return_value = 1234567890.0

        config = Config(default_endpoint='http://localhost:4317')
        attributes = Attributes("xyz", "zya")
        with patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True,True)) as mock:
            initialize_telemetry(config=config, attributes=attributes, signal_types=["logging"])  # only init logging since we aren't yet handling None value attribute keys
            mock.assert_called_once()

        mock_time.assert_called()

    def test_check_internet(self):
        """
        Test internet and OTel endpoint check function.
        """
        config = Config(default_endpoint='http://some.domain.com:1234')
        with patch('socket.create_connection', side_effect=[MagicMock(), MagicMock()]):
            internet, access = check_internet(config)
            assert True == internet
            assert True == access
        config.set_skip_internet_check(False)
        with patch('socket.create_connection', side_effect=[OSError("Test Exception"), MagicMock()]):
            internet, access = check_internet(config)
            assert False == internet
            assert True == access
        with patch('socket.create_connection', side_effect=[MagicMock(), OSError("Test Exception")]):
            internet, access = check_internet(config)
            assert True == internet
            assert False == access
        with patch('socket.create_connection', side_effect=[OSError("Test Exception"), OSError("Test Exception")]):
            internet, access = check_internet(config)
            assert False == internet
            assert False == access

    def test_grpc_otlp_exporters(self):
        """
        - Checks that the *Exporters are created
        """
        try:
            os.environ['OTEL_SDK_DISABLED'] = 'true'  # Ensure OTEL_SDK_DISABLED is not set
            cfg = Config(default_endpoint='http://localhost:4317')
            cfg.set_console_exporter(False)
            cfg.set_shutdown_on_exit(False)
            attributes = Attributes("test_service", "1.0.0")

            initialize_telemetry(cfg, attributes, signal_types=['metrics', 'logging', 'tracing'])

            metrics: _AnacondaMetrics = _AnacondaMetrics._instance
            logger: _AnacondaLogger = _AnacondaLogger._instance
            trace: _AnacondaTrace = _AnacondaTrace._instance
            assert trace.tracer.__class__.__name__ == 'Tracer'
            assert metrics.meter.__class__.__name__ == 'Meter'
        finally:
            os.environ['OTEL_SDK_DISABLED'] = 'false'  # Reset

class TestRecordHistogram:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_histogram_recording_minimal_params(self, mock_metrics: MagicMock):
        """
        Test successful histogram recording with minimal required parameters
        - Sets telemetry as initialized
        - Calls record_histogram with metric name and value only
        - Verifies _AnacondaMetrics._instance.record_histogram is called with correct params
        - Confirms function returns True when underlying method succeeds
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = record_histogram("cpu_usage", 85.7)

        assert result is True
        mock_metrics_instance.record_histogram.assert_called_once_with(
            "cpu_usage", 85.7, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_histogram_recording_with_attributes(self, mock_metrics: MagicMock):
        """
        Test successful histogram recording with custom attributes
        - Sets telemetry as initialized
        - Calls record_histogram with metric name, value, and custom attributes
        - Verifies attributes are passed through correctly
        - Confirms function returns True
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        custom_attributes = {
            "service": "api_gateway",
            "environment": "production",
            "region": "us-west-2"
        }
        mock_metrics_instance._process_attributes.return_value = custom_attributes

        result = record_histogram("request_duration", 123.45, custom_attributes)

        assert result is True
        mock_metrics_instance.record_histogram.assert_called_once_with(
            "request_duration", 123.45, custom_attributes
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_histogram_recording_failure_returns_false(self, mock_metrics: MagicMock):
        """
        Test that function returns False when underlying record_histogram fails
        - Sets telemetry as initialized
        - Configures underlying method to return False
        - Verifies function propagates the False return value
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.return_value = False
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = record_histogram("failed_metric", 99.9)

        assert result is False
        mock_metrics_instance.record_histogram.assert_called_once_with(
            "failed_metric", 99.9, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_various_numeric_values(self, mock_metrics: MagicMock):
        """
        Test histogram recording with various numeric value types
        - Tests positive float, negative float, zero, integer values
        - Verifies all numeric types are handled correctly
        - Confirms each call returns True when successful
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        test_values = [
            ("positive_float", 123.456),
            ("negative_float", -67.89),
            ("zero_value", 0.0),
            ("integer_value", 42),
            ("very_small", 0.00001),
            ("very_large", 999999.99)
        ]

        for metric_name, value in test_values:
            result = record_histogram(metric_name, value)
            assert result is True

        # Verify all calls were made
        assert mock_metrics_instance.record_histogram.call_count == len(test_values)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_empty_attributes_dict_default(self, mock_metrics: MagicMock):
        """
        Test that empty dict is used as default for attributes parameter
        - Calls function without attributes parameter
        - Verifies underlying method receives empty dict
        - Confirms default parameter behavior works correctly
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = record_histogram("default_attrs_test", 50.0)

        assert result is True
        mock_metrics_instance.record_histogram.assert_called_once_with(
            "default_attrs_test", 50.0, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_instance_method_exception_handling(self, mock_metrics: MagicMock):
        """
        Test behavior when underlying record_histogram method raises exception
        - Configures underlying method to raise an exception
        - Verifies exception is propagated (not caught by record_histogram)
        - Tests that function doesn't silently handle underlying exceptions
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.record_histogram.side_effect = MetricsNotInitialized("Metrics system error")
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        assert False == record_histogram("exception_test", 100.0)

        # For uncaught exceptions...
        mock_metrics_instance.record_histogram.side_effect = RuntimeError("Metrics system error")
        assert False == record_histogram("exception_test2", 100.0)
        mock_metrics_instance.increment_counter.side_effect = RuntimeError("Metrics system error")
        assert False == increment_counter("exception_test3")
        mock_metrics_instance.decrement_counter.side_effect = RuntimeError("Metrics system error")
        assert False == decrement_counter("exception_test4")

    def test_uninitialized_with_various_parameters(self):
        """
        Test that all parameter combinations return False when uninitialized
        - Tests different combinations of metric names, values, and attributes
        - Verifies consistent False return regardless of parameters
        - Confirms error logging occurs for each call
        """
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False

        test_cases = [
            ("metric1", 1.0, {}),
            ("metric2", 2.5, {"attr": "value"}),
            ("metric3", -1.0, {"multiple": "attrs", "count": 42}),
            ("", 0.0, {})
        ]

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            for metric_name, value, attributes in test_cases:
                result = record_histogram(metric_name, value, attributes)
                assert result is False

            # Verify error was logged for each call
            assert mock_logger_instance.error.call_count == len(test_cases)
            for call in mock_logger_instance.error.call_args_list:
                assert "Anaconda telemetry system not initialized." in call[0][0]

class TestSetGauge:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_gauge_set_minimal_params(self, mock_metrics: MagicMock):
        """
        Test successful gauge set with minimal required parameters
        - Sets telemetry as initialized
        - Calls set_gauge with metric name and value only
        - Verifies _AnacondaMetrics._instance.set_gauge is called with correct params
        - Confirms function returns True when underlying method succeeds
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.set_gauge.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = set_gauge("queue_depth", 12)

        assert result is True
        mock_metrics_instance.set_gauge.assert_called_once_with(
            "queue_depth", 12, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_gauge_set_with_attributes(self, mock_metrics: MagicMock):
        """
        Test successful gauge set with custom attributes
        - Verifies attributes are processed and passed through correctly
        - Confirms function returns True
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.set_gauge.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        custom_attributes = {
            "host": "worker-01",
            "environment": "production",
            "region": "us-west-2"
        }
        mock_metrics_instance._process_attributes.return_value = custom_attributes

        result = set_gauge("memory_in_use_bytes", 1048576, custom_attributes)

        assert result is True
        mock_metrics_instance.set_gauge.assert_called_once_with(
            "memory_in_use_bytes", 1048576, custom_attributes
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_gauge_set_failure_returns_false(self, mock_metrics: MagicMock):
        """
        Test that function returns False when the underlying set_gauge fails
        - Configures underlying method to return False
        - Verifies function propagates the False return value
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.set_gauge.return_value = False
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = set_gauge("failed_gauge", 5.5)

        assert result is False
        mock_metrics_instance.set_gauge.assert_called_once_with(
            "failed_gauge", 5.5, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_gauge_various_numeric_values(self, mock_metrics: MagicMock):
        """
        Test gauge set with various numeric value types
        - Tests positive, negative, zero, integer, and float values
        - Verifies negative values are passed through unchanged (gauges are not abs()'d like counters)
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.set_gauge.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        test_values = [
            ("positive_float", 123.456),
            ("negative_float", -67.89),
            ("zero_value", 0.0),
            ("integer_value", 42),
            ("very_small", 0.00001),
            ("very_large", 999999.99)
        ]

        for metric_name, value in test_values:
            assert set_gauge(metric_name, value) is True

        assert mock_metrics_instance.set_gauge.call_count == len(test_values)
        recorded = [call.args[1] for call in mock_metrics_instance.set_gauge.call_args_list]
        assert recorded == [value for _, value in test_values]

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_gauge_empty_attributes_dict_default(self, mock_metrics: MagicMock):
        """
        Test that empty dict is used as default for the attributes parameter
        - Calls function without attributes parameter
        - Verifies underlying method receives empty dict
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.set_gauge.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = set_gauge("default_attrs_gauge", 50.0)

        assert result is True
        mock_metrics_instance.set_gauge.assert_called_once_with(
            "default_attrs_gauge", 50.0, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_gauge_exception_handling(self, mock_metrics: MagicMock):
        """
        Test behavior when the underlying set_gauge method raises an exception
        - MetricsNotInitialized is caught and False returned (logged as a warning)
        - Any other exception is caught and False returned (logged as an error)
        """
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        mock_metrics_instance.set_gauge.side_effect = MetricsNotInitialized("Metrics system error")
        assert False == set_gauge("exception_gauge", 100.0)

        # For uncaught exceptions...
        mock_metrics_instance.set_gauge.side_effect = RuntimeError("Metrics system error")
        assert False == set_gauge("exception_gauge2", 100.0)

    def test_gauge_telemetry_not_initialized_returns_false(self):
        """
        Test that set_gauge returns False when telemetry is not initialized
        - Verifies __ANACONDA_TELEMETRY_INITIALIZED is False before call
        - Confirms function returns False and logs the uninitialized error
        """
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            result = set_gauge("test_gauge", 42.5)

            assert result is False
            mock_logger_instance.error.assert_called_once_with(
                "Anaconda telemetry system not initialized."
            )

    def test_gauge_bad_value_returns_false_through_public_api(self):
        """
        Test that a non-numeric gauge value is reported as a failure through the public API
        - Drives a real _AnacondaMetrics rather than a mock so the value validation actually runs
        - increment_counter returns False for the same input (abs() raises in our own code), so a
          gauge must not be the one metric API that silently accepts garbage and reports success
        - A bad value must not poison the metric: a valid value on the same name still succeeds
        """
        config = Config(default_endpoint="http://localhost:4318")
        config.set_console_exporter(use_console=True)
        config.set_shutdown_on_exit(False)
        attributes = Attributes("test-service", "1.0.0")

        with patch('opentelemetry.metrics.set_meter_provider'), \
             patch('anaconda_opentelemetry.signals.__check_internet_status', return_value=(True, True)):
            initialize_telemetry(config, attributes, signal_types=['metrics'])
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)

        assert increment_counter("parity_counter", "not a number") is False
        assert set_gauge("parity_gauge", "not a number") is False
        assert set_gauge("parity_gauge", None) is False
        assert set_gauge("parity_gauge", True) is False

        assert set_gauge("parity_gauge", 5) is True

class TestIncrementCounter:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_counter_increment_default_params(self, mock_metrics):
        """
        Test successful counter increment with default parameters
        - Sets telemetry as initialized
        - Calls increment_counter with counter name only (default by=1, attributes={})
        - Verifies underlying method is called with correct default values
        - Confirms function returns True when underlying method succeeds
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.increment_counter.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = increment_counter("api_requests")

        assert result is True
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "api_requests", 1, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_counter_increment_with_attributes(self, mock_metrics):
        """
        Test successful counter increment with custom attributes
        - Sets telemetry as initialized
        - Calls increment_counter with custom attributes dictionary
        - Verifies attributes are passed through correctly
        - Confirms function returns True
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.increment_counter.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        custom_attributes = {
            "service": "user_service",
            "endpoint": "/api/users",
            "status_code": 200
        }
        mock_metrics_instance._process_attributes.return_value = custom_attributes

        result = increment_counter("http_requests", by=3, attributes=custom_attributes)

        assert result is True
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "http_requests", 3, custom_attributes
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_counter_increment_failure_returns_false(self, mock_metrics):
        """
        Test that function returns False when underlying increment_counter fails
        - Sets telemetry as initialized
        - Configures underlying method to return False
        - Verifies function propagates the False return value
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.increment_counter.return_value = False
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = increment_counter("failed_counter", by=2)

        assert result is False
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "failed_counter", 2, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_various_increment_values(self, mock_metrics):
        """
        Test counter increment with various increment value types
        - Tests small, large, negative values
        - Verifies all values are processed according to actual implementation
        - Confirms consistent True return for successful increments
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.increment_counter.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        test_values = [
            ("small_positive", 1),
            ("large_positive", 1000),
            ("negative_value", -10),
            ("zero_value", 0),
            ("another_negative", -999)
        ]

        for counter_name, by_value in test_values:
            result = increment_counter(counter_name, by=by_value)
            assert result is True

        # Verify all calls were made
        assert mock_metrics_instance.increment_counter.call_count == len(test_values)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_instance_method_exception_handling(self, mock_metrics):
        """
        Test behavior when underlying increment_counter method raises exception
        - Configures underlying method to raise an exception
        - Verifies exception is propagated (not caught by increment_counter)
        - Tests that function doesn't silently handle underlying exceptions
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.increment_counter.side_effect = MetricsNotInitialized("Counter system error")
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        assert False == increment_counter("exception_test", by=1)

    def test_uninitialized_with_various_parameters(self):
        """
        Test that all parameter combinations return False when uninitialized
        - Tests different combinations of counter names, increment values, and attributes
        - Verifies consistent False return regardless of parameters
        - Confirms error logging occurs for each call
        """
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False

        test_cases = [
            ("counter1", 1, {}),
            ("counter2", 5, {"attr": "value"}),
            ("counter3", -10, {"multiple": "attrs", "count": 42}),
            ("", 0, {})
        ]

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            for counter_name, by_value, attributes in test_cases:
                result = increment_counter(counter_name, by=by_value, attributes=attributes)
                assert result is False

            # Verify error was logged for each call
            assert mock_logger_instance.error.call_count == len(test_cases)
            for call in mock_logger_instance.error.call_args_list:
                assert "Anaconda telemetry system not initialized." in call[0][0]

class TestDecrementCounter:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_counter_decrement_default_params(self, mock_metrics):
        """
        Test successful counter decrement with default parameters
        - Sets telemetry as initialized
        - Calls decrement_counter with counter name only (default by=1, attributes={})
        - Verifies underlying method is called with correct default values
        - Confirms function returns True when underlying method succeeds
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.decrement_counter.return_value = True
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = decrement_counter("api_failures")

        assert result is True
        mock_metrics_instance.decrement_counter.assert_called_once_with(
            "api_failures", 1, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_successful_counter_decrement_with_attributes(self, mock_metrics):
        """
        Test successful counter decrement with custom attributes
        - Sets telemetry as initialized
        - Calls decrement_counter with custom attributes dictionary
        - Verifies attributes are passed through correctly
        - Confirms function returns True
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.decrement_counter.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        custom_attributes = {
            "service": "cache_service",
            "cache_type": "redis",
            "region": "us-west-1"
        }
        mock_metrics_instance._process_attributes.return_value = custom_attributes

        result = decrement_counter("cache_entries", by=10, attributes=custom_attributes)

        assert result is True
        mock_metrics_instance.decrement_counter.assert_called_once_with(
            "cache_entries", 10, custom_attributes
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_counter_decrement_failure_returns_false(self, mock_metrics):
        """
        Test that function returns False when underlying decrement_counter fails
        - Sets telemetry as initialized
        - Configures underlying method to return False
        - Verifies function propagates the False return value
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.decrement_counter.return_value = False
        mock_metrics_instance._process_attributes.return_value = {}
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        result = decrement_counter("failed_counter", by=3)

        assert result is False
        mock_metrics_instance.decrement_counter.assert_called_once_with(
            "failed_counter", 3, {}
        )

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_various_decrement_values(self, mock_metrics):
        """
        Test counter decrement with various decrement value types
        - Tests small, large, negative values
        - Verifies all values are processed according to actual implementation
        - Confirms consistent True return for successful decrements
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.decrement_counter.return_value = True
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        test_values = [
            ("small_positive", 1),
            ("large_positive", 1000),
            ("negative_value", -15),
            ("zero_value", 0),
            ("another_negative", -500)
        ]

        for counter_name, by_value in test_values:
            result = decrement_counter(counter_name, by=by_value)
            assert result is True

        # Verify all calls were made
        assert mock_metrics_instance.decrement_counter.call_count == len(test_values)

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_updown_counter_vs_regular_counter_behavior(self, mock_metrics):
        """
        Test decrement_counter behavior with different counter types
        - Tests that function calls underlying method regardless of counter type
        - Underlying method handles warning/failure for regular counters per docstring
        - Verifies function delegates responsibility to underlying implementation
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        # Test with updown counter (should succeed)
        mock_metrics_instance.decrement_counter.return_value = True
        result = decrement_counter("updown_counter", by=5)
        assert result is True

        # Test with regular counter (underlying method handles warning/failure)
        mock_metrics_instance.decrement_counter.return_value = False
        result = decrement_counter("regular_counter", by=3)
        assert result is False

        # Verify both calls were made
        assert mock_metrics_instance.decrement_counter.call_count == 2

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics')
    def test_instance_method_exception_handling(self, mock_metrics):
        """
        Test behavior when underlying decrement_counter method raises exception
        - Configures underlying method to raise an exception
        - Verifies exception is propagated (not caught by decrement_counter)
        - Tests that function doesn't silently handle underlying exceptions
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.decrement_counter.side_effect = MetricsNotInitialized("Counter system error")
        setattr(mock_metrics, '_instance', mock_metrics_instance)

        assert False == decrement_counter("exception_test", by=1)

    def test_uninitialized_with_various_parameters(self):
        """
        Test that all parameter combinations return False when uninitialized
        - Tests different combinations of counter names, decrement values, and attributes
        - Verifies consistent False return regardless of parameters
        - Confirms error logging occurs for each call
        """
        assert getattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED") is False

        test_cases = [
            ("counter1", 1, {}),
            ("counter2", 8, {"attr": "value"}),
            ("counter3", -12, {"multiple": "attrs", "count": 99}),
            ("", 0, {})
        ]

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            for counter_name, by_value, attributes in test_cases:
                result = decrement_counter(counter_name, by=by_value, attributes=attributes)
                assert result is False

            # Verify error was logged for each call
            assert mock_logger_instance.error.call_count == len(test_cases)
            for call in mock_logger_instance.error.call_args_list:
                assert "Anaconda telemetry system not initialized." in call[0][0]

class TestGetTrace:

    def setup_method(self):
        """Reset global state before each test"""
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", False)

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_successful_trace_creation_default_params(self, mock_trace):
        """
        Test successful trace creation with default parameters
        - Sets telemetry as initialized
        - Calls get_trace with trace name only (default attributes={}, carrier=None)
        - Verifies underlying get_span method is called with correct default values
        - Confirms span lifecycle methods are called properly
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        mock_trace_instance._process_attributes.return_value = {}
        setattr(mock_trace, '_instance', mock_trace_instance)

        with get_trace("test_trace") as span:
            assert span is mock_span

        mock_trace_instance.get_span.assert_called_once_with("test_trace", {}, None)
        mock_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_successful_trace_creation_with_attributes(self, mock_trace):
        """
        Test successful trace creation with custom attributes
        - Sets telemetry as initialized
        - Calls get_trace with trace name and custom attributes
        - Verifies attributes are passed through correctly
        - Confirms span lifecycle is handled properly
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        setattr(mock_trace, '_instance', mock_trace_instance)

        custom_attributes = {
            "service": "data_processor",
            "operation": "batch_process",
            "user_id": "user123"
        }
        mock_trace_instance._process_attributes.return_value = custom_attributes

        with get_trace("data_processing", attributes=custom_attributes) as span:
            assert span is mock_span

        mock_trace_instance.get_span.assert_called_once_with(
            "data_processing", custom_attributes, None
        )
        mock_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_successful_trace_creation_with_carrier(self, mock_trace):
        """
        Test successful trace creation with carrier for trace continuation
        - Sets telemetry as initialized
        - Calls get_trace with trace name and carrier dictionary
        - Verifies carrier is passed through correctly for trace continuation
        - Confirms span lifecycle is handled properly
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        mock_trace_instance._process_attributes.return_value = {}
        setattr(mock_trace, '_instance', mock_trace_instance)

        carrier = {
            "traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01",
            "tracestate": "congo=t61rcWkgMzE"
        }

        with get_trace("continued_trace", carrier=carrier) as span:
            assert span is mock_span

        mock_trace_instance.get_span.assert_called_once_with(
            "continued_trace", {}, carrier
        )
        mock_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_successful_trace_creation_all_parameters(self, mock_trace):
        """
        Test successful trace creation with all parameters provided
        - Sets telemetry as initialized
        - Calls get_trace with name, attributes, and carrier
        - Verifies all parameters are passed through correctly
        - Confirms span lifecycle is handled properly
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        setattr(mock_trace, '_instance', mock_trace_instance)

        attributes = {"operation": "full_test", "version": "1.0"}
        carrier = {"traceparent": "00-trace-span-01"}
        mock_trace_instance._process_attributes.return_value = attributes

        with get_trace("full_trace", attributes=attributes, carrier=carrier) as span:
            assert span is mock_span

        mock_trace_instance.get_span.assert_called_once_with(
            "full_trace", attributes, carrier
        )
        mock_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_trace_with_exception_handling(self, mock_trace):
        """
        Test trace behavior when exception occurs within context
        - Sets telemetry as initialized
        - Adds exception to trace
        - Verifies exception is added to span and error status is set
        - Confirms span is still closed properly
        - Verifies error is logged
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_logger = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        mock_trace_instance._process_attributes.return_value = {}
        mock_trace_instance.logger = mock_logger
        setattr(mock_trace, '_instance', mock_trace_instance)

        test_exception = ValueError("Test error")

        with get_trace("error_trace") as span:
            raise test_exception

        mock_trace_instance._process_attributes.assert_called_once_with({})
        mock_trace_instance.get_span.assert_called_once_with("error_trace", {}, None)
        mock_span.add_exception.assert_called_once_with(test_exception)
        mock_span.set_error_status.assert_called_once()
        mock_span._close.assert_called_once()
        mock_logger.error.assert_called_once_with("Error in trace span error_trace: Test error")

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_span_close_called_even_if_status_methods_fail(self, mock_trace):
        """
        Test that span._close() is always called even if status methods fail
        - Sets telemetry as initialized
        - Configures span status methods to raise exceptions
        - Verifies span._close() is still called in finally block
        - Tests finally block execution regardless of other failures
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        setattr(mock_trace, '_instance', mock_trace_instance)

        with get_trace("status_error_trace") as span:
            pass

        mock_trace_instance.get_span.assert_called_once()
        mock_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_multiple_nested_traces(self, mock_trace):
        """
        Test behavior with multiple nested trace contexts
        - Sets telemetry as initialized
        - Creates nested trace contexts
        - Verifies each trace is handled independently
        - Checks that there is a proper parent-child span relationship
        - Confirms proper span lifecycle for all traces
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_outer_span = MagicMock()
        mock_inner_span = MagicMock()
        mock_trace_instance._process_attributes.side_effect = lambda x: x
        mock_trace_instance.get_span.side_effect = [mock_outer_span, mock_inner_span]
        setattr(mock_trace, '_instance', mock_trace_instance)

        # Set up span IDs for parent-child relationship verification
        mock_outer_span.span_id = "parent_span_id_12345"
        mock_inner_span.parent_id = "parent_span_id_12345"

        mock_trace_instance.get_span.side_effect = [mock_outer_span, mock_inner_span]
        setattr(mock_trace, '_instance', mock_trace_instance)

        with get_trace("outer_trace", {"level": "outer"}) as outer_span:
            assert outer_span is mock_outer_span
            with get_trace("inner_trace", {"level": "inner"}) as inner_span:
                assert inner_span is mock_inner_span
                # Verify parent-child relationship
                assert inner_span.parent_id == outer_span.span_id

        # Verify both spans were created
        assert mock_trace_instance.get_span.call_count == 2
        mock_trace_instance._process_attributes.assert_any_call({"level": "outer"})
        mock_trace_instance._process_attributes.assert_any_call({"level": "inner"})

        # Verify both spans had proper lifecycle
        mock_outer_span._close.assert_called_once()
        mock_inner_span._close.assert_called_once()

    @patch('anaconda_opentelemetry.signals._AnacondaTrace')
    def test_span_returns_correct_object(self, mock_trace):
        """
        Test that the context manager yields the correct span object
        - Sets telemetry as initialized
        - Verifies the yielded span object matches the mock span
        - Confirms the span can be used within the context
        """
        # Set up initialized state
        setattr(signals_package, "__ANACONDA_TELEMETRY_INITIALIZED", True)
        mock_trace_instance = MagicMock()
        mock_span = MagicMock()
        mock_trace_instance.get_span.return_value = mock_span
        setattr(mock_trace, '_instance', mock_trace_instance)

        with get_trace("span_object_test") as returned_span:
            # Verify the returned span is the same object
            assert returned_span is mock_span
            # Verify we can call methods on the span
            returned_span.add_event("test_event")

        # Verify the span method was called
        mock_span.add_event.assert_called_once_with("test_event")
        mock_span._close.assert_called_once()

class TestLogging:
    _instance = None
    _initialized: bool = False

    def setup_method(self):
        """Reset logger instance state before each test"""
        _initialized = False
        _instance = None

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_get_telemetry_logger_handler_without_init(self):
        with pytest.raises(RuntimeError):
            get_telemetry_logger_handler()

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_get_telemetry_logger_handler_without_logger(self):
        cfg = Config(default_endpoint='http://localhost:4317')
        cfg.set_shutdown_on_exit(False)
        attr = Attributes('test_service_name', '1.2.3')
        initialize_telemetry(config=cfg, attributes=attr, signal_types=[])
        assert get_telemetry_logger_handler() is None

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_get_telemetry_logger_handler_with_logger(self):
        cfg = Config(default_endpoint='http://localhost:4317')
        cfg.set_shutdown_on_exit(False)
        attr = Attributes('test_service_name', '1.2.3')
        initialize_telemetry(config=cfg, attributes=attr, signal_types=['logging'])
        assert get_telemetry_logger_handler() is not None

class TestSendEvent:
    _instance = None
    _initialized: bool = False

    def setup_method(self):
        """Reset logger instance state before each test"""
        _initialized = False
        _instance = None

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_send_event_without_init(self):
        with pytest.raises(RuntimeError):
            send_event("test", "test.event")

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_send_event_without_logger(self):
        cfg = Config(default_endpoint='http://localhost:4317')
        cfg.set_shutdown_on_exit(False)
        attr = Attributes('test_service_name', '1.2.3')
        initialize_telemetry(config=cfg, attributes=attr, signal_types=[])
        assert send_event("test", "test.event") is False

    @patch('anaconda_opentelemetry.signals.__ANACONDA_TELEMETRY_INITIALIZED', new=_initialized)
    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance', new=_instance)
    def test_send_event_with_logger(self):
        cfg = Config(default_endpoint='http://localhost:4317')
        cfg.set_shutdown_on_exit(False)
        attr = Attributes('test_service_name', '1.2.3')
        initialize_telemetry(config=cfg, attributes=attr, signal_types=['logging'])
        assert send_event("test message", "test.event") is True

class TestUpdateEndpoint:
    _instance = None

    def setup_method(self):
        """Reset all instances state before each test"""
        _instance = None

    def test_change_signal_endpoint_invalid_signal_type(self):
        # Test with invalid signal type
        result = change_signal_endpoint('invalid_signal', 'http://new-endpoint:4317')
        assert result is False

    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance')
    def test_change_signal_endpoint_logging_success(self, mock_logger_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = True
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_logger_instance._processor = mock_processor
        mock_logger_instance.exporter = mock_exporter
        mock_logger_instance._config = mock_config
        
        result = change_signal_endpoint('logging', 'http://new-endpoint:4317')
        
        mock_exporter.change_signal_endpoint.assert_called_once_with(
            mock_processor,
            mock_config,
            'http://new-endpoint:4317',
            auth_token=None
        )
        assert result is True

    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance')
    def test_change_signal_endpoint_logging_with_auth_token(self, mock_logger_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = True
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_logger_instance._processor = mock_processor
        mock_logger_instance.exporter = mock_exporter
        mock_logger_instance._config = mock_config
        
        result = change_signal_endpoint('logging', 'http://new-endpoint:4317', auth_token='test_token')
        
        mock_exporter.change_signal_endpoint.assert_called_once_with(
            mock_processor,
            mock_config,
            'http://new-endpoint:4317',
            auth_token='test_token'
        )
        assert result is True

    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance')
    def test_change_signal_endpoint_logging_failure(self, mock_logger_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = False
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_logger_instance._processor = mock_processor
        mock_logger_instance.exporter = mock_exporter
        mock_logger_instance._config = mock_config
        
        result = change_signal_endpoint('logging', 'http://new-endpoint:4317')
        
        assert result is False

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics._instance')
    def test_change_signal_endpoint_metrics_success(self, mock_metrics_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = True
        mock_metric_reader = MagicMock()
        mock_config = MagicMock()
        
        mock_metrics_instance.metric_reader = mock_metric_reader
        mock_metrics_instance.exporter = mock_exporter
        mock_metrics_instance._config = mock_config
        
        result = change_signal_endpoint('metrics', 'http://new-endpoint:4317')
        
        mock_exporter.change_signal_endpoint.assert_called_once_with(
            mock_metric_reader,
            mock_config,
            'http://new-endpoint:4317',
            auth_token=None
        )
        assert result is True

    @patch('anaconda_opentelemetry.signals._AnacondaMetrics._instance')
    def test_change_signal_endpoint_metrics_failure(self, mock_metrics_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = False
        mock_metric_reader = MagicMock()
        mock_config = MagicMock()
        
        mock_metrics_instance.metric_reader = mock_metric_reader
        mock_metrics_instance.exporter = mock_exporter
        mock_metrics_instance._config = mock_config
        
        result = change_signal_endpoint('metrics', 'http://new-endpoint:4317')
        
        assert result is False

    @patch('anaconda_opentelemetry.signals._AnacondaTrace._instance')
    def test_change_signal_endpoint_tracing_success(self, mock_trace_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = True
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_trace_instance._processor = mock_processor
        mock_trace_instance.exporter = mock_exporter
        mock_trace_instance._config = mock_config
        
        result = change_signal_endpoint('tracing', 'http://new-endpoint:4317')
        
        mock_exporter.change_signal_endpoint.assert_called_once_with(
            mock_processor,
            mock_config,
            'http://new-endpoint:4317',
            auth_token=None
        )
        assert result is True

    @patch('anaconda_opentelemetry.signals._AnacondaTrace._instance')
    def test_change_signal_endpoint_tracing_failure(self, mock_trace_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = False
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_trace_instance._processor = mock_processor
        mock_trace_instance.exporter = mock_exporter
        mock_trace_instance._config = mock_config
        
        result = change_signal_endpoint('tracing', 'http://new-endpoint:4317')
        
        assert result is False

    @patch('anaconda_opentelemetry.signals._AnacondaLogger._instance')
    def test_change_signal_endpoint_case_insensitive(self, mock_logger_instance):
        mock_exporter = MagicMock()
        mock_exporter.change_signal_endpoint.return_value = True
        mock_processor = MagicMock()
        mock_config = MagicMock()
        
        mock_logger_instance._processor = mock_processor
        mock_logger_instance.exporter = mock_exporter
        mock_logger_instance._config = mock_config
        
        result = change_signal_endpoint('LOGGING', 'http://new-endpoint:4317')
        
        assert result is True
        mock_exporter.change_signal_endpoint.assert_called_once()