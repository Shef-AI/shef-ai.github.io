# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import sys, time, json
sys.path.append("./")

import anaconda_opentelemetry.signals
from anaconda_opentelemetry.attributes import ResourceAttributes as Attributes
from anaconda_opentelemetry.common import _AnacondaCommon as AnacondaTelBase
from anaconda_opentelemetry.signals import _AnacondaLogger as AnacondaLogger
from anaconda_opentelemetry.signals import _AnacondaTrace as AnacondaTrace
from anaconda_opentelemetry.signals import _AnacondaMetrics as AnacondaMetrics
from anaconda_opentelemetry.signals import shutdown_telemetry
from anaconda_opentelemetry.config import Configuration as Config
from anaconda_opentelemetry.formatting import AttrDict, log_event_name_key
from opentelemetry.trace import Span, Tracer
from opentelemetry.metrics import Meter, Histogram
from opentelemetry.sdk.metrics import _Gauge
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.resources import Resource
from opentelemetry.context import Context

from typing import Dict, Callable, Union
import pytest, hashlib, re, logging, os
from unittest.mock import patch, MagicMock


# utility function
def read_config(config_file_path="tests/unit_tests/test_files/config.yaml"):
    if config_file_path.endswith('.yaml') or config_file_path.endswith('.yml'):
        from yaml import safe_load
        with open(config_file_path, 'r') as config_file:
            config_dict = safe_load(config_file)
    else:
        raise ValueError("Unsupported config file format. Only YAML is supported for this test.")
    return config_dict

@pytest.fixture(scope="module", autouse=True)
def setup_mock_logging():
    with patch('logging.getLogger') as mock_getLogger:
        mock_getLogger.return_value = MagicMock()
        mock_getLogger.return_value.level = logging.WARNING
        yield mock_getLogger

class TestAnacondaCommon:

    # class-wide test vars
    # default mock time value that is class wide
    time_patch_value = 1_234_567_899.0
    # name of service
    service_name = "test-service"
    # id of user - must match config file value
    user_id = "user123"

    @pytest.fixture(scope="class")
    def _patch_time(self, request):
        mp = pytest.MonkeyPatch()
        mp.setattr(time, "time", lambda: request.cls.time_patch_value)
        yield
        mp.undo()


    @pytest.fixture(scope="class")
    def AnacondaCommon(self, _patch_time, request) -> AnacondaTelBase:
        os.environ.clear()  # clear previous test environment vars
        config_values = read_config()
        config_dict, attributes = config_values['configs'], config_values['attributes']
        config_dict['entropy'] = "timestamp"  # this value is required and normally initialized by initialize_telemetry()
        config = Config(config_dict=config_dict)
        config.set_shutdown_on_exit(False)

        service_name = "test-service"
        service_version = "1.0.0"
        attributes = Attributes(service_name, service_version)
        attributes.set_attributes(foo="test")
        attributes.user_id == TestAnacondaCommon.user_id
        # initialize class for testing
        instance = AnacondaTelBase(config, attributes)

        return instance

    def test_hash_session_id_with_valid_user_id(self, AnacondaCommon: AnacondaTelBase):
        """
        Tests the hash method with both user_id and entropy_value passed
	    - Checks that method ouptut equals that of hashlib.sha256 output
        """
        # construct mock hash
        ts = int(time.time() * 1e9)  # format timestamp like in class function
        expected_combined = f"{ts}|{AnacondaCommon._user_id}|{self.service_name}"
        expected_hash = hashlib.sha256(expected_combined.encode("utf-8")).hexdigest()
        # real hash function call
        AnacondaCommon._hash_session_id(ts)

        assert AnacondaCommon._resource_attributes['session.id'] == expected_hash

    def test_hash_session_id_with_none_user_id(self, AnacondaCommon: AnacondaTelBase):
        """
        Tests the hash method with user_id equal to None and an entropy_value passed
        - Checks that the method correctly handles user_id == None by once again comparing hash output
        """
        # construct mock hash
        user_id = ''
        ts = int(self.time_patch_value * 1e9)  # format timestamp like in class function
        expected_combined = f"{ts}|{user_id}|{self.service_name}"
        expected_hash = hashlib.sha256(expected_combined.encode("utf-8")).hexdigest()
        # real hash function call
        AnacondaCommon._user_id = user_id
        AnacondaCommon._hash_session_id(ts)

        assert AnacondaCommon._resource_attributes['session.id'] == expected_hash

    def test_hash_session_id_with_no_entropy_value(self, AnacondaCommon: AnacondaTelBase):
        """
        - Checks that the method throws a KeyError exception if entropy_value is None
        - Asserted string must match exact Exception argument
        """

        # real hash function call
        with pytest.raises(KeyError) as exception:
            AnacondaCommon._hash_session_id(None)
        assert exception.value.args[0] == 'The entropy key has been removed.'

    def test_disable_session_id(self):
        """
        Tests that when disable_session_id is True, no session ID is generated
        """
        config_values = read_config()
        config_dict, attributes_dict = config_values['configs'], config_values['attributes']
        config_dict['entropy'] = "timestamp"
        config = Config(config_dict=config_dict)
        config.set_disable_session_id(True)
        config.set_shutdown_on_exit(False)

        service_name = "test-service"
        service_version = "1.0.0"
        attributes = Attributes(service_name, service_version)

        instance = AnacondaTelBase(config, attributes)

        assert instance._session_id is None
        assert 'session.id' not in instance._resource_attributes

    def test_hash_output_length(self, AnacondaCommon: AnacondaTelBase):
        """
        - Checks that the sha256 hash output is of length 64
        """
        AnacondaCommon._user_id = 'testuser'
        AnacondaCommon._hash_session_id("timestamp")
        result = AnacondaCommon._resource_attributes['session.id']

        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest should be 64 characters

    def test_client_sdk_valid_version(self, AnacondaCommon: AnacondaTelBase):
        """
        Uses regex to check that this value is valid semver
        """
        sdk_version = AnacondaCommon._resource_attributes["client.sdk.version"]
        if sdk_version == '0.0.0.devbuild':
            return
        valid_semver = re.compile(r"^\d+\.\d+\.\d+(?:\.commit\d+)?(?:\+g[0-9a-f]+)?$")

        assert bool(valid_semver.fullmatch(sdk_version))

    def test_schema_valid_version(self, AnacondaCommon: AnacondaTelBase):
        """
        Uses regex to check that this value is valid semver
        """
        schema_version = AnacondaCommon._resource_attributes["schema.version"]
        valid_semver = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

        assert bool(valid_semver.fullmatch(schema_version))

    def test_resource_attributes(self, AnacondaCommon: AnacondaTelBase):
        """
        - Checks that all required keys exist in resource_attributes
        - Checks that all keys have a value not equal to None
        """
        resource_attributes = AnacondaCommon.resource.attributes

        # Ensure keys and values are str or None
        for k, v in resource_attributes.items():
            assert isinstance(k, str), f"Key {k} is not a string"
            assert isinstance(v, (str, type(None))), f"Value for key '{k}' is not a string or None"

        # Required fields that must have non-None values
        required_common_attributes = [
            "service.name",
            "service.version",
            "client.sdk.version",
            "schema.version",
            "os.type",
            "os.version",
            "python.version",
            "hostname",
            "session.id",
            "environment"
        ]

        for key in required_common_attributes:
            assert key in resource_attributes, f"Missing required key: {key}"
            assert resource_attributes[key] is not None, f"Required key '{key}' has None value"

    def test_create_resource(self, AnacondaCommon: AnacondaTelBase):
        """
        - Checks that the resource created by AnacondaCommon is of type Resource
        """
        assert isinstance(AnacondaCommon.resource, Resource) is True

    def test_json_stringify_on_parameters(self, AnacondaCommon: AnacondaTelBase):
        """
        - Checks that the resource attribute parameters is JSON stringified
        """
        assert AnacondaCommon._resource_attributes['parameters'] == json.dumps({"foo": "test"})

    def test_process_attributes_added(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        AnacondaCommon._user_id = 'user123'
        attributes = {
            "key1": "val1",
            "key2": "val2"
        }
        output_attributes = AnacondaCommon._process_attributes(attributes.copy())
        attributes.update({'user.id': 'user123'})
        assert output_attributes == attributes
        assert 'user_id' not in output_attributes

    def test_process_attributes_noop(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        AnacondaCommon._user_id = None
        attributes = {
            "key1": "val1",
            "key2": "val2"
        }
        output_attributes = AnacondaCommon._process_attributes(attributes.copy())
        assert 'user.id' not in output_attributes
        assert 'user_id' not in output_attributes

    def test_process_attributes_existing(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        AnacondaCommon._user_id = 'testuser'
        attributes = {
            "key1": "val1",
            "key2": "val2",
            "user.id": "testuser"
        }
        output_attributes = AnacondaCommon._process_attributes(attributes.copy())
        assert output_attributes == attributes
        assert 'user_id' not in output_attributes

    def test_process_attributes_empty(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        AnacondaCommon._user_id = None
        output_attributes = AnacondaCommon._process_attributes()
        assert output_attributes == {}

    def test_process_attributes_none(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        with patch.object(AnacondaCommon, 'logger') as mock_logger:
            AnacondaCommon._user_id = None
            output_attributes = AnacondaCommon._process_attributes(None)
            assert output_attributes == {}
            mock_logger.debug.assert_called_once_with(
                "Attributes `None` are not a dictionary, they are not valid. They will be converted to an empty one."
            )

    def test_process_attributes_int(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that the pull_user_id method works as expected
        """
        with patch.object(AnacondaCommon, 'logger') as mock_logger:
            AnacondaCommon._user_id = None
            output_attributes = AnacondaCommon._process_attributes(123)
            assert output_attributes == {}
            mock_logger.debug.assert_called_once_with(
                "Attributes `123` are not a dictionary, they are not valid. They will be converted to an empty one."
            )

    def test_process_attributes_invalid_keys(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that only invalid keys are dropped, valid keys are preserved
        """
        with patch.object(AnacondaCommon, 'logger') as mock_logger:
            AnacondaCommon._user_id = None
            output_attributes = AnacondaCommon._process_attributes({1: "val", 2: False, "valid": "test"})
            assert output_attributes == {"valid": "test"}
            mock_logger.debug.assert_called_once_with(
                "Dropping attributes with invalid keys: [1, 2]"
            )

    def test_process_attributes_none_keys(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that only None keys are dropped, valid keys are preserved
        """
        with patch.object(AnacondaCommon, 'logger') as mock_logger:
            AnacondaCommon._user_id = None
            output_attributes = AnacondaCommon._process_attributes({None: "val", "valid_key": "valid_val"})
            assert output_attributes == {"valid_key": "valid_val"}
            mock_logger.debug.assert_called_once_with(
                "Dropping attributes with invalid keys: [None]"
            )

    def test_process_attributes_all_attrdict_types(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that all types specified in AttrDict are properly handled
        AttrDict = Dict[str, Union[str, bool, int, float, Sequence[Scalar]]]
        """
        AnacondaCommon._user_id = None
        attributes: AttrDict = {
            "str_val": "test_string",
            "bool_val": True,
            "int_val": 42,
            "float_val": 3.14,
            "list_str": ["a", "b", "c"],
            "list_int": [1, 2, 3],
            "list_bool": [True, False],
            "list_float": [1.1, 2.2],
            "list_mixed": ["x", 1, True, 2.5],
            "dict_val": {"nested": "value"}
        }
        output_attributes = AnacondaCommon._process_attributes(attributes)
        assert output_attributes["str_val"] == "test_string"
        assert output_attributes["bool_val"] == True
        assert output_attributes["int_val"] == 42
        assert output_attributes["float_val"] == 3.14
        assert output_attributes["list_str"] == ("a", "b", "c")
        assert output_attributes["list_int"] == (1, 2, 3)
        assert output_attributes["list_bool"] == (True, False)
        assert output_attributes["list_float"] == (1.1, 2.2)
        assert output_attributes["list_mixed"] == ("x", 1, True, 2.5)
        assert "dict_val" not in output_attributes

    def test_process_attributes_list_with_uuid_skipped(self, AnacondaCommon: AnacondaTelBase):
        """
        Checks that _process_attributes skips lists containing non-primitive types like UUID objects
        """
        import uuid
        AnacondaCommon._user_id = None
        attributes: AttrDict = {
            "ids": [uuid.uuid4(), uuid.uuid4()],
            "valid": [1, 2, 3]
        }
        output_attributes = AnacondaCommon._process_attributes(attributes)
        assert "ids" not in output_attributes
        assert output_attributes["valid"] == (1, 2, 3)


class TestAnacondaLogger:
    instance: AnacondaLogger = None
    # default mock time value that is class wide
    time_patch_value = 1234567899.0

    @patch('opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter')
    def test_setup_logging_http(self,  mock_exporter_http: MagicMock):
        """
        - Checks that the OTLPLogExporter from grpc library was called once
        """
        config = Config(default_endpoint="http://localhost:4317")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')

        _ = AnacondaLogger(config, attr)

        mock_exporter_http.assert_called_once()

    @patch('opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter')
    def test_setup_logging_grpc(self,  mock_exporter_grpc: MagicMock):
        """
        - Checks that the OTLPLogExporter from grpc library was called once
        """
        config = Config(default_endpoint="grpc://localhost:4317")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        _ = AnacondaLogger(config, attr)

        mock_exporter_grpc.assert_called_once()

    def test_get_log_level(self):
        """
        Uses a dictionary mappings to check that log levels returned by the method match their expected return value
        """
        test_cases = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "warn": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "fatal": logging.CRITICAL,
            "": logging.DEBUG,
            "INFO": logging.INFO,        # uppercase input
            "WaRnInG": logging.WARNING,  # mixed case input
        }
        # with patch('anaconda_opentelemetry.signals._AnacondaLogger._inject_otel_logging'):
        alogger = AnacondaLogger(Config(default_endpoint='http://localhost:4317'),
                                Attributes(service_name='test_name', service_version='0.0.0'))
        for input_str, expected in test_cases.items():
            result = alogger._get_log_level(input_str)
            assert result == expected, f"Expected {expected} for input '{input_str}', got {result}"

    def test_log_event_name_key_value(self):
        """
        Ensures log_event_name_key is always 'log.event.name'. This test will fail if the constant is changed.
        """
        assert log_event_name_key == 'log.event.name'

    def test_log_handler_injects_default_event_name(self):
        """
        Checks that the logging handler's filter injects log.event.name='__LOG__' on log records.
        """
        config = Config(default_endpoint='http://localhost:4317')
        config.set_shutdown_on_exit(False)
        alogger = AnacondaLogger(config,
                                 Attributes(service_name='test_name', service_version='0.0.0'))
        handler = alogger._get_log_handler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=None, exc_info=None
        )
        assert not hasattr(record, log_event_name_key)
        handler.handle(record)
        assert getattr(record, log_event_name_key) == '__LOG__'

class TestAnacondaTrace:
    instance: AnacondaTrace = None
    logger: logging.Logger = None

    @pytest.fixture(scope="class")
    def AnacondaTracer(self) -> AnacondaTrace:
        from opentelemetry import trace
        if TestAnacondaTrace.instance is None:
            TestAnacondaTrace.logger = MagicMock()
            config_values = read_config()
            config_dict = config_values['configs']
            config_dict['entropy'] = "timestamp"  # this value is required and normally initialized by initialize_telemetry()
            config = Config(default_endpoint='http://localhost:4317')
            config.set_shutdown_on_exit(False)
            attributes = Attributes("test-service", "1.0.0")
            with patch('opentelemetry.trace.set_tracer_provider'),\
                 patch('opentelemetry.sdk.trace.export.ConsoleSpanExporter'):
                TestAnacondaTrace.instance = AnacondaTrace(config, attributes)
                TestAnacondaTrace.instance.use_console_exporters = False
                TestAnacondaTrace.instance.logger = TestAnacondaTrace.logger

        yield TestAnacondaTrace.instance

        # trace.get_tracer_provider().shutdown()
        TestAnacondaTrace.instance = None

    @pytest.fixture
    def ASpanFactory(self) -> Callable[[AnacondaTrace, str, Dict[str, str]], object]:
        def _make_ASpan(AnacondaTracer, span_name: str ="test-span", attributes: Dict[str, str]={}):
            return AnacondaTracer.get_span(span_name, attributes)
        return _make_ASpan

    def test_ASpan_get_span(
            self,
            AnacondaTracer: AnacondaTrace,
            ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that ASpan object returned by the method has a property name of instance string and > length 0
        - Checks that ASpan object returned also has a property span of type Span (otel sdk object)
        - Checks that the trace_id of the Span object is > 0 and < 2**128 (valid trace id)
        - Checks that the span_id of the Span object is > 0 and < 2**64 (valid span id)
        """
        ASpan = ASpanFactory(AnacondaTracer, span_name="test-span", attributes={"test": "1"})

        assert isinstance(ASpan._name, str)
        assert len(ASpan._name) > 0
        assert isinstance(ASpan._span, Span)

        trace_id = ASpan._span.get_span_context().trace_id
        span_id = ASpan._span.get_span_context().span_id

        # test that span and trace ids are valid
        assert isinstance(trace_id, int)
        assert isinstance(span_id, int)

    def test_ASpan_get_span_no_span_name_no_attrs(
            self,
            AnacondaTracer: AnacondaTrace,
            ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        Performs the same checks as the previous test, but in the case that span_name and attributes are both equal to None
        """
        ASpan = ASpanFactory(AnacondaTracer, span_name=None, attributes=None)

        # test that ASpan was created
        assert isinstance(ASpan._span, Span)

        trace_id = ASpan._span.get_span_context().trace_id
        span_id = ASpan._span.get_span_context().span_id

        # test that span and trace ids are valid
        assert isinstance(trace_id, int)
        assert isinstance(span_id, int)

    @patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter')
    def test_setup_tracing_http(
        self,
        mock_exporter_http: MagicMock,
        AnacondaTracer: AnacondaTrace
    ):
        """
        - Checks that the tracer object returned by the method is of type Tracer (otel sdk object)
        - Checks that the OTLPSpanExporter from http library a called once
        """

        config = Config(default_endpoint="http://localhost")
        config.set_shutdown_on_exit(False)
        tracer = AnacondaTracer._setup_tracing(config)
        mock_exporter_http.assert_called_once()

        # Assert tracer is a valid Tracer object
        assert isinstance(tracer, Tracer)

    @patch('opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter')
    def test_setup_tracing_grpc(
        self,
        mock_exporter_grpc: MagicMock,
        AnacondaTracer: AnacondaTrace
    ):
        """
        - Checks that the tracer object returned by the method is of type Tracer (otel sdk object)
        - Checks that the OTLPSpanExporter from grpc library was called once
        """
        AnacondaTracer._request_protocol = 'grpc'
        config = Config(default_endpoint="grpc://localhost")
        config.set_shutdown_on_exit(False)
        tracer = AnacondaTracer._setup_tracing(config)
        mock_exporter_grpc.assert_called_once()

        # Assert tracer is a valid Tracer object
        assert isinstance(tracer, Tracer)

    def test_ASpan_add_event_valid_name(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that the `get_span` method still returns a valid Span object
        - Checks that the ASpan.span object's most recent event name matches the expected event name
        """
        span_name = "test-span"
        ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})

        event_str = "hello"
        ASpan.add_event(event_str)

        # there is a span event on init indicating start so we test most recent
        assert isinstance(ASpan._span, Span)

    def test_ASpan_add_event_no_name(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that the get_span method still returns a valid Span object
        - Checks that the ASpan.span object's most recent event name matches the expected event name when None is passed
        """
        span_name = "test-span"
        ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})

        event_str = None
        ASpan.add_event(event_str)

        # assert that we still have an instance of span
        assert isinstance(ASpan._span, Span)

    def test_ASpan_add_exception_valid_exception(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks again that `get_span` returns a valid Span object
        - Checks that the most recent event name for the ASpan.span object matches the expected event name after an exception is passed
        - Checks that the "error.message" attribute for the ASpan.span object matches the expected err_msg
        """
        span_name = "test-span"
        ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})
        err_msg = "This is a test exception"
        exception = Exception(err_msg)
        ASpan.add_exception(exception)

        # there is a span event on init indicating start so we test most recent
        assert isinstance(ASpan._span, Span)

    def test_ASpan_add_exception_none_exception(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that the get_span method still returns a valid Span object
        - Checks that the "error.message" attribute for the ASpan.span object matches the expected generic error message for when None is passed as the exception
        """
        span_name = "test-span"
        ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})
        exception = None
        ASpan.add_exception(exception)

        # generic_err_msg is hard coded as the fallback case in _AnacondaTrace.ASpan
        generic_err_msg = "Generic exception because the exception passed was None."

        assert isinstance(ASpan._span, Span)

    def test_ASpan_set_error_status(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that ASpan.status == StatusCode.ERROR after the method is called
        """
        span_name = "test-span"
        ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})
        ASpan.set_error_status()
        # The Span object is opaque, cannot check if it was set.

    def test_ASpan_add_attributes(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks add_attributes method adds attributes to the ASpan.span object.
        """
        span_name = "test-span"
        ASpan: AnacondaTrace.ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})
        ASpan._noop = False
        ASpan._span = MagicMock()
        assert len(ASpan._attributes) == 1  # initial attributes
        ASpan.add_attributes({"key1": "value1", "key2": "value2"})
        golden_attributes = {
            "key1": "value1",
            "key2": "value2",
            "test": "1"  # existing attributes should not be overwritten
        }
        assert len(ASpan._attributes) == len(golden_attributes)
        for key in golden_attributes.keys():
            assert ASpan._attributes[key] == golden_attributes[key]

        with pytest.raises(TypeError):
            # Test that TypeError is raised when non-dict is passed
            ASpan.add_attributes("not a dict")

        ASpan._noop = True  # Simulate noop span
        ASpan.add_attributes({"key3": "value3"})

        assert len(ASpan._attributes) == len(golden_attributes)
        for key in golden_attributes.keys():
            assert ASpan._attributes[key] == golden_attributes[key]

        ASpan._noop = False  # Simulate noop span
        ASpan.set_error_status()

        ASpan._close()

    def test_ASpan_close_event(
        self,
        AnacondaTracer: AnacondaTrace,
        ASpanFactory: Callable[[AnacondaTrace, str, Dict[str, str]], object]
    ):
        """
        - Checks that the most recent span event after this method is called is one with end in the name
        """
        span_name = "test-span"
        ASpan: AnacondaTrace.ASpan = ASpanFactory(AnacondaTracer, span_name=span_name, attributes={"test": "1"})
        ASpan._noop = True
        assert isinstance(ASpan._span, Span)
        ASpan._close()

    def test_carrier_creates_parent_child_relationship(
        self,
        AnacondaTracer: AnacondaTrace
    ):
        """
        Tests that carrier propagates trace context between spans.
        - Parent and child share trace_id
        - Parent and child have different span_ids
        - Carrier gets populated with context
        """
        carrier = {}
        parent = AnacondaTracer.get_span("parent", {}, carrier)
        parent_trace = parent._span.get_span_context().trace_id
        parent_span = parent._span.get_span_context().span_id

        assert len(carrier) > 0, "Carrier should contain trace context"

        child = AnacondaTracer.get_span("child", {}, carrier)
        child_trace = child._span.get_span_context().trace_id
        child_span = child._span.get_span_context().span_id

        assert child_trace == parent_trace, "Child should share parent's trace_id"
        assert child_span != parent_span, "Child should have different span_id"

        child._close()
        parent._close()


    def test_carrier_none_creates_independent_traces(
        self,
        AnacondaTracer: AnacondaTrace
    ):
        """
        Tests that no carrier or separate carriers create independent traces.
        """
        span1 = AnacondaTracer.get_span("span1", {}, None)
        span2 = AnacondaTracer.get_span("span2", {}, None)

        assert span1._span.get_span_context().trace_id != \
            span2._span.get_span_context().trace_id, \
            "Spans without carrier should have different trace_ids"

        carrier1, carrier2 = {}, {}
        span3 = AnacondaTracer.get_span("span3", {}, carrier1)
        span4 = AnacondaTracer.get_span("span4", {}, carrier2)

        assert span3._span.get_span_context().trace_id != \
            span4._span.get_span_context().trace_id, \
            "Separate carriers should create separate traces"

        for span in [span1, span2, span3, span4]:
            span._close()


    def test_multiple_spans_share_trace_via_carrier(
        self,
        AnacondaTracer: AnacondaTrace
    ):
        """
        Tests that multiple spans using same carrier share the trace.
        """
        carrier = {}
        spans = []
        trace_ids = []
        span_ids = []

        for i in range(3):
            span = AnacondaTracer.get_span(f"span-{i}", {}, carrier)
            spans.append(span)
            trace_ids.append(span._span.get_span_context().trace_id)
            span_ids.append(span._span.get_span_context().span_id)

        assert len(set(trace_ids)) == 1, "All spans should share trace_id"
        assert len(set(span_ids)) == 3, "Each span should have unique span_id"

        for span in reversed(spans):
            span._close()

class TestAnacondaMetrics:
    instance: AnacondaMetrics = None

    @pytest.fixture(scope="class")
    def AnacondaMetric(self) -> AnacondaMetrics:
        from opentelemetry import metrics
        if TestAnacondaMetrics.instance is None:
            config_values = read_config()
            config_dict, attributes_dict = config_values['configs'], config_values['attributes']
            config_dict['entropy'] = "timestamp"  # this value is required and normally initialized by initialize_telemetry()
            config = Config(config_dict=config_dict)
            config.set_shutdown_on_exit(False)
            attributes = Attributes("test-service", "1.0.0")
            attributes.set_attributes(**attributes_dict)
            # initialize class for testing
            with patch('opentelemetry.metrics.set_meter_provider'):
                TestAnacondaMetrics.instance = AnacondaMetrics(config, attributes)
                TestAnacondaMetrics.instance.use_console_exporters = False
                TestAnacondaMetrics.instance.logger = MagicMock()

        yield TestAnacondaMetrics.instance

        # metrics.get_meter_provider().shutdown()
        TestAnacondaMetrics.instance = None

    @patch('opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter')
    def test_setup_metrics_http(self, mock_exporter_http: MagicMock, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that metrics object returned by the method is of type Meter (otel sdk object)
        - Checks that http library is called for exporter
        """
        mock_exporter_http.__name__ = 'OTLPMetricExporter'
        config = Config(default_endpoint="http://localhost")
        config.set_shutdown_on_exit(False)
        metrics = AnacondaMetric._setup_metrics(config)
        mock_exporter_http.assert_called_once()

        # ensure returned object is of type Meter
        assert isinstance(metrics, Meter)

    @patch('opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter')
    def test_setup_metrics_grpc(self, mock_exporter_grpc: MagicMock, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that metrics object returned by the method is of type Meter (otel sdk object)
        - Checks that grpc library is called for exporter
        """
        config = Config(default_endpoint="grpc://localhost")
        config.set_shutdown_on_exit(False)
        metrics = AnacondaMetric._setup_metrics(config)
        mock_exporter_grpc.assert_called_once()

        # ensure returned object is of type Meter
        assert isinstance(metrics, Meter)

    def test_catch_space_in_metric_name(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that the logger logs a warning matching the invalid regex string when an invalid metric name is passed
        - Checks that meter objects is an empty dict, meaning nothing has been initialized
        """
        AnacondaMetric.logger = MagicMock()
        name = "hello world"
        AnacondaMetric._get_or_create_metric(name)

        AnacondaMetric.logger.warning.assert_called_once_with(
            f"Metric {name} does not match valid regex: r\"^[A-Za-z][A-Za-z_0-9.]*[A-Za-z_0-9]$\""
        )
        assert AnacondaMetric.type_list["simple_up_down_counter"] == {}

    def test_setup_manual_metrics_invalid_type(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that the logger logs a warning matching the invalid type string when an invalid metric type is passed
        - Checks that meter objects is an empty dict, meaning nothing has been initialized
        """
        AnacondaMetric.logger = MagicMock()
        AnacondaMetric.create_dispatcher = {
            "simple_counter": MagicMock()
        }
        name = "bad_type_metric"
        type = "not_real_type"

        with pytest.raises(RuntimeError):
            AnacondaMetric._get_or_create_metric(name, metric_type=type)

    def test_setup_manual_metrics_success(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that the simple_counter dispatcher was called exactly once with arguments matching name, unit, and desc
        - Checks that meter objects contains a key of the newly added metric name
        """
        # this function must go after all the empty dict assertions
        # scope of the AnacondaMetric is the class so new manual metrics persist

        create_mock = MagicMock()
        AnacondaMetric.create_dispatcher = {
            'simple_counter': create_mock
        }

        name = "test_counter"
        desc = "A test counter"
        unit = "1"

        AnacondaMetric._get_or_create_metric(name, metric_type='simple_counter', units=unit, description=desc)

        create_mock.assert_called_once_with(
            name, unit=unit, description=desc
        )
        assert name in AnacondaMetric.type_list['simple_counter']

    def test_record_histogram_success(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True given assembled inputs
        - Checks that _Histogram was called exactly once with expected arguments
        """
        mock_metric = MagicMock()

        # Inject a fake metric into the instance
        AnacondaMetric.type_list["histogram"]['my_histogram'] = mock_metric

        value = 42.0

        result = AnacondaMetric.record_histogram("my_histogram", value, {"tag": "test"})

        assert result is True
        mock_metric.record.assert_called_once_with(value, {"tag": "test"})

    def test_set_gauge_success(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True given assembled inputs
        - Checks that _Gauge.set was called exactly once with expected arguments
        """
        mock_metric = MagicMock()

        # Inject a fake metric into the instance
        AnacondaMetric.type_list["gauge"]['my_gauge'] = mock_metric

        value = 17.5

        result = AnacondaMetric.set_gauge("my_gauge", value, {"tag": "test"})

        assert result is True
        mock_metric.set.assert_called_once_with(value, {"tag": "test"})

    def test_set_gauge_default_attributes(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True after correctly falling back to default attributes
        - Checks that _Gauge.set was called exactly once with an empty attributes dict
        """
        mock_metric = MagicMock()

        AnacondaMetric.type_list["gauge"]['default_gauge'] = mock_metric

        result = AnacondaMetric.set_gauge("default_gauge", 3)

        assert result is True
        mock_metric.set.assert_called_once_with(3, {})

    def test_set_gauge_negative_and_zero_values(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that gauge values are passed through unmodified, unlike counters which use abs()
        """
        mock_metric = MagicMock()

        AnacondaMetric.type_list["gauge"]['signed_gauge'] = mock_metric

        for value in (-42.5, 0, 99):
            assert AnacondaMetric.set_gauge("signed_gauge", value) is True

        assert [call.args[0] for call in mock_metric.set.call_args_list] == [-42.5, 0, 99]

    def test_set_gauge_reuses_existing_metric(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that repeated calls with the same name do not create a new gauge object
        """
        create_mock = MagicMock()
        saved_dispatcher = AnacondaMetric.create_dispatcher
        AnacondaMetric.create_dispatcher = {'gauge': create_mock}
        try:
            AnacondaMetric.type_list["gauge"].pop('reused_gauge', None)

            assert AnacondaMetric.set_gauge("reused_gauge", 1) is True
            assert AnacondaMetric.set_gauge("reused_gauge", 2) is True

            create_mock.assert_called_once_with(
                "reused_gauge", unit='#', description='Dynamically create gauge metric.'
            )
            assert create_mock.return_value.set.call_count == 2
        finally:
            AnacondaMetric.create_dispatcher = saved_dispatcher

    def test_set_gauge_invalid_name_returns_false(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that an invalid metric name is rejected, logged, and no gauge is created
        """
        AnacondaMetric.logger = MagicMock()
        name = "1_bad gauge"

        assert AnacondaMetric.set_gauge(name, 5) is False

        AnacondaMetric.logger.warning.assert_called_once_with(
            f"Metric {name} does not match valid regex: r\"^[A-Za-z][A-Za-z_0-9.]*[A-Za-z_0-9]$\""
        )
        assert name not in AnacondaMetric.type_list["gauge"]

    def test_metric_name_ending_with_period_rejected(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that metric names ending with a period are rejected
        """
        AnacondaMetric.logger = MagicMock()
        name = "metric.name."

        assert AnacondaMetric.set_gauge(name, 5) is False

        AnacondaMetric.logger.warning.assert_called_once_with(
            f"Metric {name} does not match valid regex: r\"^[A-Za-z][A-Za-z_0-9.]*[A-Za-z_0-9]$\""
        )
        assert name not in AnacondaMetric.type_list["gauge"]

    @pytest.mark.parametrize("value", ["7", None, True, False, [1], {"a": 1}, object()])
    def test_set_gauge_non_numeric_value_returns_false(self, value, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that a non-numeric gauge value is rejected before reaching the otel instrument
        - Rejecting up front matters because otel's Gauge.set() accepts anything and the failure
          would otherwise surface at serialization, discarding the entire export batch
        - bool is rejected too; it is an int subclass but never a meaningful gauge reading
        """
        AnacondaMetric.logger = MagicMock()
        mock_metric = MagicMock()
        AnacondaMetric.type_list["gauge"]['rejecting_gauge'] = mock_metric

        assert AnacondaMetric.set_gauge("rejecting_gauge", value) is False

        mock_metric.set.assert_not_called()
        AnacondaMetric.logger.error.assert_called_once_with(
            f"Metric 'rejecting_gauge' gauge value must be an int or float, not {type(value).__name__}."
        )

    @pytest.mark.parametrize("value", [0, 42, -42, 0.0, 12.5, -0.001])
    def test_set_gauge_accepts_int_and_float(self, value, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that valid numeric values still pass validation and reach the instrument unmodified
        """
        mock_metric = MagicMock()
        AnacondaMetric.type_list["gauge"]['numeric_gauge'] = mock_metric

        assert AnacondaMetric.set_gauge("numeric_gauge", value) is True

        mock_metric.set.assert_called_once_with(value, {})

    def test_set_gauge_bad_value_does_not_create_metric(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that a rejected value short-circuits before the gauge object is created, so a bad
          call cannot register an instrument as a side effect
        """
        AnacondaMetric.logger = MagicMock()
        create_mock = MagicMock()
        saved_dispatcher = AnacondaMetric.create_dispatcher
        AnacondaMetric.create_dispatcher = {'gauge': create_mock}
        try:
            assert AnacondaMetric.set_gauge("never_created_gauge", "not a number") is False

            create_mock.assert_not_called()
            assert 'never_created_gauge' not in AnacondaMetric.type_list["gauge"]
        finally:
            AnacondaMetric.create_dispatcher = saved_dispatcher

    def test_increment_counter_success_counter(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns False given correctly assembled inputs
        - Checks that _Counter was called exactly once with expected arguments
        """
        mock_metric = MagicMock()
        mock_metric.__class__.__name__ = "_Counter"

        AnacondaMetric.type_list["simple_counter"]["my_counter"] = mock_metric

        unit = 3
        result = AnacondaMetric.increment_counter("my_counter", by=unit, attributes={"tag": "test"})

        assert result is True
        mock_metric.add.assert_called_once_with(unit, {"tag": "test"})

    def test_increment_counter_success_updowncounter(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True given assembled inputs
        - Checks that _UpDownCounter was called exactly once with expected arguments
        """
        mock_metric = MagicMock()
        mock_metric.__class__.__name__ = "_UpDownCounter"

        AnacondaMetric.type_list["simple_up_down_counter"]["my_updown"] = mock_metric

        result = AnacondaMetric.increment_counter("my_updown", by=-2, attributes={"reason": "decrement"})

        assert result is True
        mock_metric.add.assert_called_once_with(2, {"reason": "decrement"})

    def test_increment_counter_default_by_and_attributes(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True after correctly falling back to default inputs
        - Checks that _Counter was called exactly once with expected default arguments
        """
        mock_metric = MagicMock()
        mock_metric.__class__.__name__ = "_Counter"

        AnacondaMetric.type_list["simple_counter"]["default_metric"] = mock_metric

        result = AnacondaMetric.increment_counter("default_metric")

        assert result is True
        mock_metric.add.assert_called_once_with(1, {})  # Default by=1, attributes={}

    def test_decrement_counter_success(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True given assembled inputs
        - Checks that _UpDownCounter was called exactly once with expected arguments
        """
        mock_metric = MagicMock()
        mock_metric.__class__.__name__ = "_UpDownCounter"

        AnacondaMetric.type_list["simple_up_down_counter"]["my_updown"] = mock_metric

        result = AnacondaMetric.decrement_counter("my_updown", by=3, attributes={"reason": "adjustment"})

        assert result is True
        mock_metric.add.assert_called_once_with(-3, {"reason": "adjustment"})

    def test_decrement_counter_default_arguments(self, AnacondaMetric: AnacondaMetrics):
        """
        - Checks that method returns True after correctly falling back to default inputs
        - Checks that _UpDownCounter was called exactly once with expected default arguments
        """
        mock_metric = MagicMock()
        mock_metric.__class__.__name__ = "_UpDownCounter"

        AnacondaMetric.type_list["simple_up_down_counter"]["default_case"] = mock_metric

        result = AnacondaMetric.decrement_counter("default_case")

        assert result is True
        mock_metric.add.assert_called_once_with(-1, {})  # Default by=1, attributes={}

    def test_preferred_temporality(self):
        """
        - Checks that the temporaity is cumulative when set by caller.
        """
        cfg = Config(default_endpoint="http://localhost/v1/metrics")
        cfg.set_use_cumulative_metrics(True)
        cfg.set_shutdown_on_exit(False)
        attr = Attributes("test-service", "1.0.0")
        with patch('opentelemetry.metrics.set_meter_provider'):
            metrics = AnacondaMetrics(cfg, attr)
            assert metrics._cumulative_temporality == metrics._get_temporality()

    def test_gauge_registered_on_new_instance(self):
        """
        - Checks that a freshly built instance wires 'gauge' into both the dispatcher and the type list
        - Checks that the gauge dispatcher entry is the otel Meter.create_gauge method
        """
        cfg = Config(default_endpoint="http://localhost/v1/metrics")
        cfg.set_shutdown_on_exit(False)
        attr = Attributes("test-service", "1.0.0")
        with patch('opentelemetry.metrics.set_meter_provider'):
            metrics = AnacondaMetrics(cfg, attr)

        assert metrics.create_dispatcher['gauge'] == metrics.meter.create_gauge
        assert metrics.type_list['gauge'] is metrics.gauge_objects
        assert metrics.gauge_objects == {}

    def test_gauge_temporality_always_cumulative(self):
        """
        - Checks that a gauge is CUMULATIVE in both the default and cumulative temporality maps,
          since a last-value metric has no meaningful DELTA representation
        """
        for temporality_map in (AnacondaMetrics._default_temporality, AnacondaMetrics._cumulative_temporality):
            assert temporality_map[_Gauge] == AggregationTemporality.CUMULATIVE

    def test_gauge_creates_real_otel_gauge(self):
        """
        - Checks that the create path produces a real otel SDK gauge with the expected unit and description
        - Uses the instance's own provider so a real meter (not the global proxy meter) is exercised
        """
        cfg = Config(default_endpoint="http://localhost/v1/metrics")
        cfg.set_shutdown_on_exit(False)
        attr = Attributes("test-service", "1.0.0")
        with patch('opentelemetry.metrics.set_meter_provider'):
            metrics = AnacondaMetrics(cfg, attr)

        real_meter = metrics._provider.get_meter("test-service", "1.0.0")
        metrics.meter = real_meter
        metrics.create_dispatcher['gauge'] = real_meter.create_gauge

        assert metrics.set_gauge("real_gauge", 12.5, {"host": "local"}) is True

        gauge = metrics.type_list['gauge']['real_gauge']
        assert isinstance(gauge, _Gauge)
        assert gauge.unit == '#'
        assert gauge.description == 'Dynamically create gauge metric.'

def _emitted(mock_provider):
    """Return (body, attributes) from the recorded Logger.emit call.

    ``Logger.emit`` takes keyword arguments (body=, attributes=) on
    opentelemetry-sdk >= 1.40.0 and a single positional LogRecord before that,
    so read whichever shape was used rather than assuming one.
    """
    call = mock_provider.get_logger.return_value.emit.call_args
    if call.kwargs:
        return call.kwargs["body"], call.kwargs["attributes"]
    record = call.args[0]
    return record.body, dict(record.attributes)


class TestEventLogger:
    """Tests for the EventLogger class."""

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.get_logger.return_value = MagicMock()
        return provider

    @pytest.fixture
    def event_logger(self, mock_provider):
        from anaconda_opentelemetry.logging import EventLogger
        return EventLogger(mock_provider)

    def test_init_defaults(self, mock_provider):
        from anaconda_opentelemetry.logging import EventLogger
        logger = EventLogger(mock_provider)
        mock_provider.get_logger.assert_called_with("event_logger")

    def test_init_custom_params(self, mock_provider):
        from anaconda_opentelemetry.logging import EventLogger
        logger = EventLogger(mock_provider, logger_name="custom")
        mock_provider.get_logger.assert_called_with("custom")

    def test_send_event(self, event_logger, mock_provider):
        event_logger._send_event("test message", "test.event")
        mock_logger = mock_provider.get_logger.return_value
        mock_logger.emit.assert_called_once()
        body, attributes = _emitted(mock_provider)
        assert body == "test message"
        assert attributes[log_event_name_key] == "test.event"

    def test_send_event_with_attributes(self, event_logger, mock_provider):
        attrs = {"key": "value"}
        event_logger._send_event("error msg", "error.event", attributes=attrs)
        body, attributes = _emitted(mock_provider)
        assert body == "error msg"
        assert attributes == {"key": "value", log_event_name_key: "error.event"}

    def test_send_event_missing_event_name(self, event_logger):
        """Verifies that _send_event raises TypeError when event_name is not passed."""
        with pytest.raises(TypeError):
            event_logger._send_event("message")

    def test_send_event_default_empty_attributes(self, event_logger, mock_provider):
        """Verifies that _send_event defaults to empty dict with event_name still injected."""
        event_logger._send_event("msg", "test.event")
        _, attributes = _emitted(mock_provider)
        assert attributes == {log_event_name_key: "test.event"}

    def test_send_event_body_string_passthrough(self, event_logger, mock_provider):
        """Verifies that a string body is passed through unchanged."""
        event_logger._send_event("plain text", "test.event")
        body, _ = _emitted(mock_provider)
        assert body == "plain text"
        assert isinstance(body, str)

    def test_send_event_body_dict_serialized(self, event_logger, mock_provider):
        """Verifies that a dict body is JSON-serialized."""
        body = {"status": "ok", "count": 42}
        event_logger._send_event(body, "test.event")
        emitted_body, _ = _emitted(mock_provider)
        assert emitted_body == json.dumps(body)
        assert isinstance(emitted_body, str)

    def test_send_event_body_list_serialized(self, event_logger, mock_provider):
        """Verifies that a list body is JSON-serialized."""
        body = [1, "two", {"three": 3}]
        event_logger._send_event(body, "test.event")
        emitted_body, _ = _emitted(mock_provider)
        assert emitted_body == json.dumps(body)
        assert isinstance(emitted_body, str)


class TestProxyConfig:

    def test_set_proxy_url(self):
        config = Config(default_endpoint="http://localhost:4317")
        result = config.set_proxy_url("http://proxy.example.com:8080")
        assert result is config  # returns self for chaining
        assert config._get_proxy_url() == "http://proxy.example.com:8080"

    def test_get_proxy_url_default_none(self):
        config = Config(default_endpoint="http://localhost:4317")
        assert config._get_proxy_url() is None

    def test_proxy_url_from_env(self):
        os.environ['ATEL_PROXY_URL'] = 'http://env-proxy:9090'
        try:
            config = Config(default_endpoint="http://localhost:4317")
            assert config._get_proxy_url() == 'http://env-proxy:9090'
        finally:
            del os.environ['ATEL_PROXY_URL']

    def test_create_proxy_session_returns_none_without_proxy(self):
        config = Config(default_endpoint="http://localhost:4317")
        assert config._create_proxy_session() is None

    def test_create_proxy_session_returns_session_with_proxy(self):
        import requests
        config = Config(default_endpoint="http://localhost:4317")
        config.set_proxy_url("http://proxy.example.com:8080")
        session = config._create_proxy_session()
        assert isinstance(session, requests.Session)
        assert session.proxies['http'] == "http://proxy.example.com:8080"
        assert session.proxies['https'] == "http://proxy.example.com:8080"

    def test_proxy_url_from_config_dict(self):
        config = Config(
            default_endpoint="http://localhost:4317",
            config_dict={'proxy_url': 'http://dict-proxy:1234'}
        )
        assert config._get_proxy_url() == 'http://dict-proxy:1234'

    def test_env_proxy_overrides_config_dict(self):
        os.environ['ATEL_PROXY_URL'] = 'http://env-proxy:9090'
        try:
            config = Config(
                default_endpoint="http://localhost:4317",
                config_dict={'proxy_url': 'http://dict-proxy:1234'}
            )
            assert config._get_proxy_url() == 'http://env-proxy:9090'
        finally:
            del os.environ['ATEL_PROXY_URL']


class TestBuildHttpExporterKwargs:

    @pytest.fixture
    def common_instance(self):
        config = Config(default_endpoint="http://localhost:4317")
        attributes = Attributes(service_name='test-name', service_version='0.0.0')
        return AnacondaTelBase(config, attributes)

    def test_basic_kwargs_no_proxy(self, common_instance):
        kwargs = common_instance._build_http_exporter_kwargs(
            'logging', 'http://localhost:4317/v1/logs', {'authorization': 'Bearer token'}
        )
        assert kwargs['endpoint'] == 'http://localhost:4317/v1/logs'
        assert kwargs['headers'] == {'authorization': 'Bearer token'}
        assert 'certificate_file' in kwargs
        assert 'session' not in kwargs

    def test_kwargs_with_proxy(self, common_instance):
        import requests
        common_instance._config.set_proxy_url('http://proxy:8080')
        kwargs = common_instance._build_http_exporter_kwargs(
            'tracing', 'http://localhost:4317/v1/traces', {}
        )
        assert 'session' in kwargs
        assert isinstance(kwargs['session'], requests.Session)
        assert kwargs['session'].proxies['http'] == 'http://proxy:8080'
        assert kwargs['session'].proxies['https'] == 'http://proxy:8080'

    def test_kwargs_with_extra_kwargs(self, common_instance):
        kwargs = common_instance._build_http_exporter_kwargs(
            'metrics', 'http://localhost:4317/v1/metrics', {},
            preferred_temporality={'Counter': 'DELTA'}
        )
        assert kwargs['preferred_temporality'] == {'Counter': 'DELTA'}
        assert kwargs['endpoint'] == 'http://localhost:4317/v1/metrics'

    def test_kwargs_correct_ca_cert_per_signal(self):
        config = Config(default_endpoint="http://localhost:4317")
        attributes = Attributes(service_name='test-name', service_version='0.0.0')
        instance = AnacondaTelBase(config, attributes)

        for signal in ['logging', 'tracing', 'metrics']:
            kwargs = instance._build_http_exporter_kwargs(signal, 'http://localhost', {})
            get_ca_cert = getattr(config, f"_get_ca_cert_{signal}")
            assert kwargs['certificate_file'] == get_ca_cert()

    def test_kwargs_empty_headers(self, common_instance):
        kwargs = common_instance._build_http_exporter_kwargs(
            'logging', 'http://localhost:4317/v1/logs', {}
        )
        assert kwargs['headers'] == {}


class TestProxyInSignalSetup:

    @patch('opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter')
    def test_logging_http_with_proxy(self, mock_exporter):
        config = Config(default_endpoint="http://localhost:4317")
        config.set_proxy_url("http://proxy:8080")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        logger = AnacondaLogger(config, attr)
        call_kwargs = mock_exporter.call_args
        assert 'session' in call_kwargs.kwargs or 'session' in dict(zip(
            mock_exporter.call_args_list[0].args, mock_exporter.call_args_list[0].kwargs
        ))
        # Verify session was passed through the shim's init_kwargs
        assert 'session' in logger.exporter._init_kwargs
        assert logger.exporter._init_kwargs['session'].proxies['http'] == 'http://proxy:8080'

    @patch('opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter')
    def test_logging_http_without_proxy(self, mock_exporter):
        config = Config(default_endpoint="http://localhost:4317")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        logger = AnacondaLogger(config, attr)
        assert 'session' not in logger.exporter._init_kwargs

    @patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter')
    def test_tracing_http_with_proxy(self, mock_exporter):
        config = Config(default_endpoint="http://localhost:4317")
        config.set_proxy_url("http://proxy:8080")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        with patch('opentelemetry.trace.set_tracer_provider'):
            tracer = AnacondaTrace(config, attr)
        assert 'session' in tracer.exporter._init_kwargs
        assert tracer.exporter._init_kwargs['session'].proxies['https'] == 'http://proxy:8080'

    @patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter')
    def test_tracing_http_without_proxy(self, mock_exporter):
        config = Config(default_endpoint="http://localhost:4317")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        with patch('opentelemetry.trace.set_tracer_provider'):
            tracer = AnacondaTrace(config, attr)
        assert 'session' not in tracer.exporter._init_kwargs

    @patch('opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter')
    def test_metrics_http_with_proxy(self, mock_exporter):
        mock_exporter.__name__ = 'OTLPMetricExporter'
        config = Config(default_endpoint="http://localhost:4317")
        config.set_shutdown_on_exit(False)
        config.set_proxy_url("http://proxy:8080")
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        with patch('opentelemetry.metrics.set_meter_provider'):
            metrics = AnacondaMetrics(config, attr)
        assert 'session' in metrics.exporter._init_kwargs
        assert metrics.exporter._init_kwargs['session'].proxies['http'] == 'http://proxy:8080'

    @patch('opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter')
    def test_metrics_http_without_proxy(self, mock_exporter):
        mock_exporter.__name__ = 'OTLPMetricExporter'
        config = Config(default_endpoint="http://localhost:4317")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        with patch('opentelemetry.metrics.set_meter_provider'):
            metrics = AnacondaMetrics(config, attr)
        assert 'session' not in metrics.exporter._init_kwargs

    @patch('opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter')
    def test_grpc_not_affected_by_proxy(self, mock_exporter):
        config = Config(default_endpoint="grpc://localhost:4317")
        config.set_proxy_url("http://proxy:8080")
        config.set_shutdown_on_exit(False)
        attr = Attributes(service_name='test-name', service_version='0.0.0')
        logger = AnacondaLogger(config, attr)
        assert 'session' not in logger.exporter._init_kwargs


class MockHistogram(Histogram):
    def __init__(self):
        self.counter = 0
        self.last_value = None
        self.last_attr = {}

    def record(self, amount: Union[int, float], attr: AttrDict = None, context: Context = None):
        self.counter += 1
        self.last_value = amount
        self.last_attr = attr
