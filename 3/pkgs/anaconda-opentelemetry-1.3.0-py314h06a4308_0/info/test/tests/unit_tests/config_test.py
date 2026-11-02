# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append("./")

from anaconda_opentelemetry.config import Configuration as Config

import pytest, os, json, tempfile, re
from unittest.mock import patch, MagicMock, Mock
from grpc import ChannelCredentials

class TestConfiguration:
    def test_passed_in_default_endpoint(self): # Test default endpoint
        without={}
        has={Config.DEFAULT_ENDPOINT_NAME: 'grpc://localhost:4318'}

        config1 = Config(default_endpoint='https://localhost:4317', default_auth_token="SomeAuthToken", default_private_ca_cert_file='/tmp/cert', config_dict=has)
        assert 'https://localhost:4317' == config1._get_default_endpoint()
        config2 = Config(config_dict=has)
        assert 'grpc://localhost:4318' == config2._get_default_endpoint()
        with pytest.raises(ValueError):
            Config(config_dict=without)

    def test_other_endpoints(self):
        config={
            Config.DEFAULT_ENDPOINT_NAME: ":4317",  # no host
            Config.LOGGING_ENDPOINT_NAME: "bad_host:4318",
            Config.TRACING_ENDPOINT_NAME: "bad-port:65536",
            Config.METRICS_ENDPOINT_NAME: "bad-protocol://host",
        }
        with pytest.raises(ValueError, match=f"Invalid endpoint format: :4317"):
            Config(config_dict=config)

        del config[Config.DEFAULT_ENDPOINT_NAME]
        with pytest.raises(ValueError, match=f"Invalid endpoint format: bad_host:4318"):
            Config(default_endpoint="http://localhost:4317", config_dict=config)

        del config[Config.LOGGING_ENDPOINT_NAME]
        with pytest.raises(ValueError, match=f"Invalid endpoint format: bad-port:65536"):
            Config(default_endpoint="http://localhost:4317", config_dict=config)

        del config[Config.TRACING_ENDPOINT_NAME]
        with pytest.raises(ValueError, match=f"Invalid endpoint format: bad-protocol://host"):
            Config(default_endpoint="http://localhost:4317", config_dict=config)

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://mydoamin.com:812"):  # priviledged port
            Config(default_endpoint="http://mydoamin.com:812")

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://127.0.0.1.0:1812"):
            Config(default_endpoint="http://127.0.0.1.0:1812")  # five quads, expect 4

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://127.0.0.0:1812"):
            Config(default_endpoint="http://127.0.0.0:1812")  # last quad cannot be 0

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://0.10.20.30:1812"):
            Config(default_endpoint="http://0.10.20.30:1812")  # first quad cannot be 0

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://127.327.0.1:1812"):
            Config(default_endpoint="http://127.327.0.1:1812")  # any quad cannot exceed 255.

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://255.0.0.1:1812"):
            Config(default_endpoint="http://255.0.0.1:1812")  # first quad cannot be ==255.

        with pytest.raises(ValueError, match=f"Invalid endpoint format: http://127.0.0.255:1812"):
            Config(default_endpoint="http://127.0.0.255:1812")  # last quad cannot be ==255.

        cfg = Config(default_endpoint="http://localhost:2345")
        cfg.set_logging_endpoint('http://localhost:2346', auth_token='', cert_ca_file='')
        cfg.set_metrics_endpoint('http://localhost:2347', auth_token='', cert_ca_file='')
        cfg.set_tracing_endpoint('http://localhost:2348', auth_token='', cert_ca_file='')

        with pytest.raises(ValueError):
            cfg.set_logging_endpoint('http://localhost:80000')
        with pytest.raises(ValueError):
            cfg.set_metrics_endpoint('http://local host:8000')
        with pytest.raises(ValueError):
            cfg.set_tracing_endpoint('')

        assert 'http://localhost:2345' == cfg._get_default_endpoint()
        # test endpoint path appending logic
        assert 'http://localhost:2346/v1/logs' == cfg._get_logging_endpoint()
        assert 'http://localhost:2347/v1/metrics' == cfg._get_metrics_endpoint()
        assert 'http://localhost:2348/v1/traces' == cfg._get_tracing_endpoint()

        cfg.set_logging_endpoint('http://localhost:2346/')
        assert 'http://localhost:2346/v1/logs' == cfg._get_logging_endpoint()

        with pytest.raises(ValueError, match=f"Invalid endpoint format: "):
            Config(default_endpoint="   ")  # url with whitespace
        with pytest.raises(ValueError, match=f"Invalid endpoint format: "):
            Config(default_endpoint="")  # empty url
        with pytest.raises(ValueError, match=f"Invalid endpoint format: "):
            Config(default_endpoint="https://")  # cutoff url

    def test_endpoints_as_urls(self):
        cfg = Config(default_endpoint="https://localhost:2345")
        assert True == cfg._get_TLS_default().tls  # passed https to constructor

        cfg = Config(default_endpoint="https://localhost")
        assert "https://localhost" == cfg._get_default_endpoint()  # no port

        cfg = Config(default_endpoint="https://localhost:4317/metrics/v1?query=yes")
        assert "https://localhost:4317/metrics/v1?query=yes" == cfg._get_default_endpoint()  # query params are included

        with pytest.raises(ValueError, match=re.escape("Invalid endpoint format: https://:4317/metrics/v1?query=yes&query2=no")):
            cfg = Config(default_endpoint="https://:4317/metrics/v1?query=yes&query2=no")  # bad host
        with pytest.raises(ValueError, match=re.escape("Invalid endpoint format: https://0.1.2.3:4317/metrics/v1?query=yes&query2=no")):
            cfg = Config(default_endpoint="https://0.1.2.3:4317/metrics/v1?query=yes&query2=no")  # bad host
        with pytest.raises(ValueError, match=re.escape("Invalid endpoint format: https://7.8.9.0:4317/metrics/v1?query=yes&query2=no")):
            cfg = Config(default_endpoint="https://7.8.9.0:4317/metrics/v1?query=yes&query2=no")  # bad host
        with pytest.raises(ValueError):
            cfg = Config(default_endpoint="https://local host:4317/metrics/v1")
        # test http exporter endpoint
        cfg = Config(default_endpoint="http://localhost:4317/metrics/v1")
        assert "http://localhost:4317/metrics/v1" == cfg._get_default_endpoint()  # tests default endpoint value

    def test_setters_and_getters(self):
        os.environ[f'{Config.__PREFIX__}{Config.USE_CONSOLE_EXPORTER_NAME.upper()}'] = ""
        config = Config(default_endpoint='https://mydomain.com:14317')
        os.environ[f'{Config.__PREFIX__}{Config.USE_CONSOLE_EXPORTER_NAME.upper()}'] = 'true'

        # For logging_level
        assert 'https://mydomain.com:14317' == config._get_default_endpoint()
        assert 'warning' == config._get_logging_level()

        config.set_logging_level("debug")
        assert 'debug' == config._get_logging_level()
        config.set_logging_level("unexpected")  # silent fail, can't throw in this class except __init__ and only for endpoints.
        assert 'debug' == config._get_logging_level()

        # For TLS
        assert True == config._get_TLS_default().tls  # default

        # For console_exporter
        assert False == config._get_console_exporter()  # default
        config.set_console_exporter(True)
        assert True == config._get_console_exporter()
        config.set_console_exporter(False)
        assert False == config._get_console_exporter()

        # For auth_token
        assert None == config._get_auth_token_default()  # default
        config.set_auth_token('some_long_auth_token')
        assert 'some_long_auth_token' == config._get_auth_token_default()
        config.set_auth_token(None)
        assert None == config._get_auth_token_default()

        # HTTP tls_private_ca_cert
        # Create temp file with fake cert content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----")
            f.flush()
            temp_path = f.name
            config.set_tls_private_ca_cert(temp_path)
        try:
            assert temp_path == config._get_ca_cert_default()
        finally:
            os.unlink(temp_path)

        # new config for gRPC tls_private_ca_cert
        config = Config(default_endpoint='grpcs://mydomain.com:14317')
        # Create temp file with fake cert content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----")
            f.flush()
            temp_path = f.name
            config.set_tls_private_ca_cert(temp_path)
        try:
            assert isinstance(config._get_ca_cert_default(), ChannelCredentials)
        finally:
            os.unlink(temp_path)

        config.set_tls_private_ca_cert(None)
        assert None != config._get_ca_cert_default()  # This is the creds object not the cert_file!

        # For metrics_export_interval_ms
        assert 60_000 == config._get_metrics_export_interval_ms()  # default
        config.set_metrics_export_interval_ms(10_000)
        assert 10_000 == config._get_metrics_export_interval_ms()
        with pytest.raises(TypeError):  # Must be an int type.
            config.set_metrics_export_interval_ms(None)
        config.set_metrics_export_interval_ms(-20)  # Silent fail...
        assert 10_000 == config._get_metrics_export_interval_ms()

        # For tracing_export_interval_ms
        assert 60_000 == config._get_tracing_export_interval_ms()  # default
        config.set_tracing_export_interval_ms(10_000)
        assert 10_000 == config._get_tracing_export_interval_ms()
        with pytest.raises(TypeError):  # Must be an int type.
            config.set_tracing_export_interval_ms(None)
        config.set_tracing_export_interval_ms(-20)  # Silent fail...
        assert 10_000 == config._get_tracing_export_interval_ms()

        # For tracing_session_entropy
        import time
        now=int(time.time() * 1e9)
        assert now <= config._get_tracing_session_entropy()  # default
        config.set_tracing_session_entropy(10_000)
        assert 10_000 == config._get_tracing_session_entropy()
        config.set_tracing_session_entropy('a string')
        assert 'a string' == config._get_tracing_session_entropy()
        config.set_tracing_session_entropy(None)
        assert now <= config._get_tracing_session_entropy()

    def test_default_endpoint_with_signals(self):
        cfg = Config(default_endpoint="https://localhost:9090")

        assert "https://localhost:9090/v1/logs" == cfg._get_logging_endpoint()
        assert "https://localhost:9090/v1/metrics" == cfg._get_metrics_endpoint()
        assert "https://localhost:9090/v1/traces" == cfg._get_tracing_endpoint()

        # test interaction when user specifies the path
        cfg.set_logging_endpoint("https://localhost/v1/logs")

        assert "https://localhost/v1/logs" == cfg._get_logging_endpoint()

    def test_environment_variable_endpoints(self):
        """
        Tests that when environment variables for endpoints are set, the config is also set. Implicitly tests that ENV variables will overwrite configs.
        """
        os.environ[f"{Config.__PREFIX__}{Config.LOGGING_ENDPOINT_NAME.upper()}"] = "https://logginghost:8002"
        os.environ[f"{Config.__PREFIX__}{Config.METRICS_ENDPOINT_NAME.upper()}"] = "https://metricshost:8002"
        os.environ[f"{Config.__PREFIX__}{Config.TRACING_ENDPOINT_NAME.upper()}"] = "https://tracinghost:8002"
        os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_ENDPOINT_NAME.upper()}"] = "https://testtesttest:8007"
        cfg = Config(default_endpoint="https://localhost:9090")

        assert "https://logginghost:8002/v1/logs" == cfg._get_logging_endpoint()
        assert "https://metricshost:8002/v1/metrics" == cfg._get_metrics_endpoint()
        assert "https://tracinghost:8002/v1/traces" == cfg._get_tracing_endpoint()
        assert "https://testtesttest:8007" == cfg._get_default_endpoint()

    def test_environment_variable_auth_token(self):
        """
        Tests that when environment variable for the auth token is set, the config is also set. Implicitly tests that ENV variables will overwrite configs.
        """
        os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_AUTH_TOKEN_NAME.upper()}"] = "xRT5hYU7"
        cfg = Config(default_endpoint="http://localhost:9090")

        assert "xRT5hYU7" == cfg._get_auth_token_default()

    def test_skip_internet_check(self):
        """
        Test to check the class is correctly storing the self.SKIP_INTERNET_CHECK value.
        """
        try:
            os.environ["OTEL_SDK_DISABLED"] = 'true'
            cfg = Config(default_endpoint="https://localhost:9090")
            assert True == cfg._get_skip_internet_check()
            cfg.set_skip_internet_check(False)
            assert False == cfg._get_skip_internet_check()
            del(os.environ["OTEL_SDK_DISABLED"])
            os.environ[f"{Config.__PREFIX__}{Config.SKIP_INTERNET_CHECK_NAME.upper()}"] = 'no'
            cfg = Config(default_endpoint="http://localhost:9090")
            assert False == cfg._get_skip_internet_check()
        finally:
            os.environ[f"{Config.__PREFIX__}{Config.SKIP_INTERNET_CHECK_NAME.upper()}"] = 'true'

    def test_exporter_interval_ms(self):
        cfg = Config(default_endpoint="http://localhost:9090", config_dict={Config.METRICS_EXPORT_INTERVAL_MS_NAME: 5000})
        assert 5000 == cfg._get_metrics_export_interval_ms()
        os.environ[f"{Config.__PREFIX__}{Config.METRICS_EXPORT_INTERVAL_MS_NAME.upper()}"] = "6000"
        cfg = Config(default_endpoint="http://localhost:9090", config_dict={Config.METRICS_EXPORT_INTERVAL_MS_NAME: 5000})
        assert 6000 == cfg._get_metrics_export_interval_ms()
        os.environ[f"{Config.__PREFIX__}{Config.METRICS_EXPORT_INTERVAL_MS_NAME.upper()}"] = "not_a_number"
        with pytest.raises(ValueError):
            cfg = Config(default_endpoint="http://localhost:9090", config_dict={Config.METRICS_EXPORT_INTERVAL_MS_NAME: 5000})
        del(os.environ[f"{Config.__PREFIX__}{Config.METRICS_EXPORT_INTERVAL_MS_NAME.upper()}"])

    def test_implicit_settings_tls_protocol(self):
        os.environ.clear()  # clear previous test environment vars
        cfg = Config(default_endpoint="http://localhost")
        assert False == cfg._get_TLS_default().tls
        assert 'http' == cfg._get_request_protocol_default().protocol
        cfg = Config(default_endpoint="https://localhost")
        assert True == cfg._get_TLS_default().tls
        assert 'https' == cfg._get_request_protocol_default().protocol
        cfg = Config(default_endpoint="grpc://localhost")
        assert False == cfg._get_TLS_default().tls
        assert 'grpc' == cfg._get_request_protocol_default().protocol
        cfg = Config(default_endpoint="grpcs://localhost")
        assert True == cfg._get_TLS_default().tls
        assert 'grpcs' == cfg._get_request_protocol_default().protocol

    def test_only_env_var_default_endpoint(self):
        os.environ["ATEL_DEFAULT_ENDPOINT"] = "https://localhost:8080"
        cfg = Config()
        assert "https://localhost:8080" == cfg._get_default_endpoint()

        # test nothing, ensure is raises error
        os.environ.clear()  # clear previous test environment vars
        with pytest.raises(ValueError):
            cfg = Config()

    def test_different_signal_protocols(self):
        cfg = Config(default_endpoint="http://localhost:8000")
        cfg.set_metrics_endpoint("https://test.com")
        cfg.set_logging_endpoint("grpc://localhost:8000")
        cfg.set_tracing_endpoint("grpcs://test.com:5000")

        assert cfg._get_request_protocol_metrics() == "https"
        assert cfg._get_request_protocol_logging() == "grpc"
        assert cfg._get_request_protocol_tracing() == "grpcs"
        assert cfg._get_request_protocol_default().protocol == "http"

    def test_different_signal_tokens(self):
        cfg = Config(default_endpoint="http://localhost:8000")
        cfg.set_auth_token_metrics("124")
        cfg.set_auth_token_logging("abc")
        cfg.set_auth_token_tracing("123")

        assert cfg._get_auth_token_metrics() == "124"
        assert cfg._get_auth_token_logging() == "abc"
        assert cfg._get_auth_token_tracing() == "123"

    def test_different_signal_tls_certs(self):
        # Store file paths for cleanup
        temp_files = []

        # Create 4 different cert files
        cert_contents = [
            "-----BEGIN CERTIFICATE-----\nFAKE_CA_CERT_LOG\n-----END CERTIFICATE-----\n",
            "-----BEGIN CERTIFICATE-----\nFAKE_CA_CERT_TRACE\n-----END CERTIFICATE-----\n",
            "-----BEGIN CERTIFICATE-----\nFAKE_CA_CERT_METRICS\n-----END CERTIFICATE-----\n",
            "-----BEGIN CERTIFICATE-----\nFAKE_CA_CERT_DEFAULT\n-----END CERTIFICATE-----\n"
        ]

        for _, content in enumerate(cert_contents):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
                f.write(content)
                temp_files.append(f.name)

        ca_file1, ca_file2, ca_file3, ca_file4 = temp_files

        cfg = Config(default_endpoint="http://localhost:8008")
        cfg.set_tls_private_ca_cert(ca_file4)
        cfg.set_tls_private_ca_cert_logging(ca_file1)
        cfg.set_tls_private_ca_cert_tracing(ca_file2)
        cfg.set_tls_private_ca_cert_metrics(ca_file3)

        assert cfg._get_ca_cert_default() == ca_file4
        assert cfg._get_ca_cert_logging() == ca_file1
        assert cfg._get_ca_cert_tracing() == ca_file2
        assert cfg._get_ca_cert_metrics() == ca_file3

        # switch one to grpc
        cfg.set_logging_endpoint("grpc://localhosttest")
        cfg.set_tls_private_ca_cert_logging(ca_file1)
        assert cfg._get_ca_cert_logging() != ca_file1
        assert isinstance(cfg._get_ca_cert_logging(), ChannelCredentials)

        # test default changed to none
        cfg.set_tls_private_ca_cert(None)
        assert isinstance(cfg._get_ca_cert_logging(), ChannelCredentials)
        assert cfg._get_ca_cert_tracing() == ca_file2
        assert cfg._get_ca_cert_metrics() == ca_file3

        # Cleanup
        for file_path in temp_files:
            os.unlink(file_path)

    def test_prepare_ca_cert_file_for_grpc_public_cert(self):
        cfg = Config(default_endpoint="grpcs://localhost")
        creds = cfg._prepare_ca_cert('grpcs', None) is None
        assert creds is not None

    def test_cumulative_metrics(self):
        cfg = Config(default_endpoint="grpcs://localhost")
        cfg.set_use_cumulative_metrics(True)
        assert cfg._get_use_cumulative_metrics() == True

    def test_change_signal_endpoint(self):
        """Test the _change_signal_endpoint method for different signals"""
        cfg = Config(default_endpoint="http://localhost:4317")

        new_endpoint = cfg._change_signal_endpoint("metrics", "http://newhost:8080", auth_token="token123")
        assert new_endpoint == "http://newhost:8080/v1/metrics"
        assert cfg._get_auth_token_metrics() == "token123"

        new_endpoint = cfg._change_signal_endpoint("tracing", "https://tracehost:9090")
        assert new_endpoint == "https://tracehost:9090/v1/traces"

        new_endpoint = cfg._change_signal_endpoint("logging", "grpc://loghost:4317", auth_token="logtoken")
        assert new_endpoint == "grpc://loghost:4317"
        assert cfg._get_auth_token_logging() == "logtoken"

    def test_change_signal_endpoint_preserves_path(self):
        """Test that _change_signal_endpoint preserves custom paths"""
        cfg = Config(default_endpoint="http://localhost:4317")

        new_endpoint = cfg._change_signal_endpoint("metrics", "http://custom:8080/custom/path")
        assert new_endpoint == "http://custom:8080/custom/path/v1/metrics"

        new_endpoint = cfg._change_signal_endpoint("logging", "http://host:8080/v1/logs")
        assert new_endpoint == "http://host:8080/v1/logs"

    def test_change_signal_endpoint_invalid(self):
        """Test that _change_signal_endpoint raises errors for invalid endpoints"""
        cfg = Config(default_endpoint="http://localhost:4317")

        with pytest.raises(ValueError):
            cfg._change_signal_endpoint("metrics", "http://invalid port:8080")

    def test_ignore_environment_variables(self):
        """Test that ignore_environment_variables=True prevents ATEL_* and OTEL_SDK_DISABLED from affecting config."""
        endpoint = "http://localhost:4317"
        token = "original_token"

        os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_AUTH_TOKEN_NAME.upper()}"] = "env_token"
        os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_ENDPOINT_NAME.upper()}"] = "http://envhost:9999"
        os.environ[f"{Config.__PREFIX__}{Config.SKIP_INTERNET_CHECK_NAME.upper()}"] = "true"
        os.environ["OTEL_SDK_DISABLED"] = "true"
        try:
            cfg = Config(default_endpoint=endpoint, default_auth_token=token, ignore_environment_variables=True)
            assert cfg._get_default_endpoint() == endpoint
            assert cfg._get_auth_token_default() == token
            assert cfg._get_skip_internet_check() == False
        finally:
            del os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_AUTH_TOKEN_NAME.upper()}"]
            del os.environ[f"{Config.__PREFIX__}{Config.DEFAULT_ENDPOINT_NAME.upper()}"]
            del os.environ[f"{Config.__PREFIX__}{Config.SKIP_INTERNET_CHECK_NAME.upper()}"]
            del os.environ["OTEL_SDK_DISABLED"]


