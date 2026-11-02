# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# config.py
"""
Anaconda Telemetry - Configuration Module

This module provides the configuration setting from a file or a dictionary (or both)
"""

from typing import Dict, Any, List
import re, os, grpc, warnings, functools

"""
Configuration class to supply settings for Anaconda Telemetry.
It allows loading configuration from a JSON or YAML file, or from a dictionary.
It validates the format of endpoints and ensures they conform to the expected structure.
"""


def deprecated(func):
    # This is a decorator to mark functions as deprecated.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} is deprecated and will be removed in a future version.",
            category=DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper


class Configuration:
    """
    Configuration class to supply settings for Anaconda Telemetry. For environment variables make these capitalized and
    prepend with 'ATEL\\_' and remove suffix '\\_NAME'. For example, the environment variable for the default endpoint would
    be 'ATEL_DEFAULT_ENDPOINT'. The environment variable for the logging endpoint would be 'ATEL_LOGGING_ENDPOINT'. The bool
    values can be represented by "1", "yes", "true" case-insensitive and all other values are considered False.

    - DEFAULT_ENDPOINT_NAME - Name for the default endpoint in the configuration files or dictionaries passed into this class.
    - LOGGING_ENDPOINT_NAME - Name for the logging endpoint in the configuration files or dictionaries passed into this class.
    - TRACING_ENDPOINT_NAME - Name for the tracing endpoint in the configuration files or dictionaries passed into this class.
    - METRICS_ENDPOINT_NAME - Name for the metrics endpoint in the configuration files or dictionaries passed into this class.
    - USE_CONSOLE_EXPORTER_NAME - Name for the console exporter flag in the configuration files or dictionaries passed into this class.
    - DEFAULT_AUTH_TOKEN_NAME - Name for the default authentication token in the configuration files or dictionaries passed into this class.
    - LOGGING_AUTH_TOKEN_NAME - Name for the logging authentication token in the configuration files or dictionaries passed into this class.
    - TRACING_AUTH_TOKEN_NAME - Name for the tracing authentication token in the configuration files or dictionaries passed into this class.
    - METRICS_AUTH_TOKEN_NAME - Name for the metrics authentication token in the configuration files or dictionaries passed into this class.
    - METRICS_EXPORT_INTERVAL_MS_NAME - Name for the metrics export interval in milliseconds in the configuration files or dictionaries passed into this class.
    - TRACING_EXPORT_INTERVAL_MS_NAME - Name for the tracing export interval in milliseconds in the configuration files or dictionaries passed into this class.
    - LOGGING_LEVEL_NAME - Name for the logging level in the configuration files or dictionaries passed into this class.
    - SESSION_ENTROPY_VALUE_NAME - Name for the session entropy value in the configuration files or dictionaries passed into this class.
    - TLS_PRIVATE_CA_CERT_FILE_NAME - File name for the TLS private CA certificate in the configuration files or dictionaries passed into this class.
    - SKIP_INTERNET_CHECK_NAME - If you are running in an environment that does not have access to the internet, set this to True.
    - USE_CUMULATIVE_METRICS_NAME - If aggregating data in the client is required for Counter, or Histogram set this to a True state.
    - PROXY_URL_NAME - Used to set the proxy for telemetry exporters in this package
    - SHUTDOWN_ON_EXIT_NAME - If True (default), providers register atexit handlers that flush on interpreter exit. If False, the caller must manually call shutdown_telemetry() or flush_telemetry() before the process exits.
    - VERBOSE_EXPORT_ERRORS_NAME - If False (default), OpenTelemetry export errors are suppressed. If True, export errors such as "Transient error" will be logged.
    - DISABLE_SESSION_ID_NAME - If True, disables automatic session ID generation. If False (default), a session ID is generated and added to telemetry.

    To initializes the Configuration instance.

    config = Configuration(default_endpoint='example.com:4317').set_auth_token('<token_here>')

    Args:
        default_endpoint (str): Default endpoint in the form '<IPv4|domain_name>:<port>'.
        config_dict (Dict[str,Any], optional): Optional dictionary containing configuration settings.
    """
    __PREFIX__ = 'ATEL_'

    DEFAULT_ENDPOINT_NAME           = 'default_endpoint'
    LOGGING_ENDPOINT_NAME           = 'logging_endpoint'
    TRACING_ENDPOINT_NAME           = 'tracing_endpoint'
    METRICS_ENDPOINT_NAME           = 'metrics_endpoint'
    USE_CONSOLE_EXPORTER_NAME       = 'use_console_exporter'
    DEFAULT_AUTH_TOKEN_NAME         = 'default_auth_token'
    LOGGING_AUTH_TOKEN_NAME         = 'logging_auth_token'
    TRACING_AUTH_TOKEN_NAME         = 'tracing_auth_token'
    METRICS_AUTH_TOKEN_NAME         = 'metrics_auth_token'
    METRICS_EXPORT_INTERVAL_MS_NAME = 'metrics_export_interval_ms'
    TRACING_EXPORT_INTERVAL_MS_NAME = 'tracing_export_interval_ms'
    LOGGING_LEVEL_NAME              = 'logging_level'
    SESSION_ENTROPY_VALUE_NAME      = 'session_entropy_value'
    DEFAULT_CA_CERT_NAME            = 'default_credentials'
    LOGGING_CA_CERT_NAME            = 'logging_credentials'
    TRACING_CA_CERT_NAME            = 'tracing_credentials'
    METRICS_CA_CERT_NAME            = 'metrics_credentials'
    SKIP_INTERNET_CHECK_NAME        = 'skip_internet_check'
    USE_CUMULATIVE_METRICS_NAME     = 'use_cumulative_metrics'
    PROXY_URL_NAME                  = 'proxy_url'
    SHUTDOWN_ON_EXIT_NAME           = 'shutdown_on_exit'
    VERBOSE_EXPORT_ERRORS_NAME      = 'verbose_export_errors'
    DISABLE_SESSION_ID_NAME         = 'disable_session_id'

    _base_names: List[str] = [
        DEFAULT_ENDPOINT_NAME,
        LOGGING_ENDPOINT_NAME,
        TRACING_ENDPOINT_NAME,
        METRICS_ENDPOINT_NAME,
        USE_CONSOLE_EXPORTER_NAME,
        DEFAULT_AUTH_TOKEN_NAME,
        LOGGING_AUTH_TOKEN_NAME,
        TRACING_AUTH_TOKEN_NAME,
        METRICS_AUTH_TOKEN_NAME,
        METRICS_EXPORT_INTERVAL_MS_NAME,
        TRACING_EXPORT_INTERVAL_MS_NAME,
        LOGGING_LEVEL_NAME,
        SESSION_ENTROPY_VALUE_NAME,
        DEFAULT_CA_CERT_NAME,
        LOGGING_CA_CERT_NAME,
        TRACING_CA_CERT_NAME,
        METRICS_CA_CERT_NAME,
        SKIP_INTERNET_CHECK_NAME,
        USE_CUMULATIVE_METRICS_NAME,
        PROXY_URL_NAME,
        SHUTDOWN_ON_EXIT_NAME,
        VERBOSE_EXPORT_ERRORS_NAME,
        DISABLE_SESSION_ID_NAME,
    ]

    _endpoint_names: List[str] = [
        DEFAULT_ENDPOINT_NAME,
        LOGGING_ENDPOINT_NAME,
        TRACING_ENDPOINT_NAME,
        METRICS_ENDPOINT_NAME
    ]

    _credential_names: List[str] = [
        DEFAULT_CA_CERT_NAME,
        LOGGING_CA_CERT_NAME,
        TRACING_CA_CERT_NAME,
        METRICS_CA_CERT_NAME
    ]

    _auth_token_names: List[str] = [
        DEFAULT_AUTH_TOKEN_NAME,
        LOGGING_AUTH_TOKEN_NAME,
        TRACING_AUTH_TOKEN_NAME,
        METRICS_AUTH_TOKEN_NAME
    ]

    _bool_value_names: List[str] = [
        USE_CONSOLE_EXPORTER_NAME,
        SKIP_INTERNET_CHECK_NAME,
        USE_CUMULATIVE_METRICS_NAME,
        SHUTDOWN_ON_EXIT_NAME,
        VERBOSE_EXPORT_ERRORS_NAME,
        DISABLE_SESSION_ID_NAME,
    ]

    _int_value_names: List[str] = [
        METRICS_EXPORT_INTERVAL_MS_NAME
    ]

    def __init__(self, default_endpoint: str = None, default_auth_token: str = None,
                 default_private_ca_cert_file: str = None, config_dict: Dict[str, Any] = {},
                 ignore_environment_variables: bool = False):
        """
        Creates the configuration object passed to initialize_telemetry.

        Args:
            default_endpoint (str): The endpoint used when not specifying a specific endpoint for a specific signal type. May be None.
            default_auth_token (str): The default auth token use for the default_endpoint or None.
            default_private_ca_cert_file (str): File name for the private cert file if used or None. Not used frequently.
            config_dict (Dict[str,any]): An initialization map to configure the object in bulk or {}.
            ignore_environment_variables (bool): If True, all ATEL_* environment variables and OTEL_SDK_DISABLED are
                                                 ignored. Only values passed via constructor arguments and config_dict
                                                 are used. Defaults to False.

        Raises:
            ValueError: If there is no `default_endpoint` value passed to its arguments or in the `config_dict` kwarg,
                        and no `ATEL_DEFAULT_ENDPOINT` environment variable set.
            ValueError: Non integer value set for `ATEL_METRICS_EXPORT_INTERVAL_MS_NAME`
        """
        self._config: Dict[str, Any] = {}
        self._config.update(config_dict)

        if default_endpoint is not None:
            endpoint = self._Endpoint(default_endpoint)
            self._config[self.DEFAULT_ENDPOINT_NAME] = endpoint.url

        if default_auth_token is not None:
            self._config[self.DEFAULT_AUTH_TOKEN_NAME] = default_auth_token

        if default_private_ca_cert_file is not None:
            self._config[self.DEFAULT_CA_CERT_NAME] = default_private_ca_cert_file

        # Merge environment variables into the config
        if not ignore_environment_variables:
            for base_name in self._base_names:
                env_name = f"{self.__PREFIX__}{base_name.upper()}"
                env_value = os.environ.get(env_name, None)
                if env_value is not None:
                    self._config[base_name] = env_value.strip()

        # Ensure default endpoint is set
        if self.DEFAULT_ENDPOINT_NAME not in self._config.keys():
            raise ValueError(f"A '{self.DEFAULT_ENDPOINT_NAME}' must be provided or set in the configuration.")

        # Check environment vars for endpoints and normalize endpoints
        self._endpoints = {}
        for endpoint_name in self._endpoint_names:
            if endpoint_name in self._config:
                # set endpoint object for this signal (or default)
                self._endpoints[endpoint_name] = self._Endpoint(self._config[endpoint_name])
                # set endpoint config value for this signal (or default)
                self._config[endpoint_name] = self._endpoints[endpoint_name].url

        # Normalize bool values
        for bool_name in self._bool_value_names:
            if bool_name in self._config and isinstance(self._config[bool_name], str):
                self._config[bool_name] = self._config[bool_name].lower().strip() in ['true', 'yes', '1', 'on']

        # Special case OTEL_SDK_DISABLED...
        if not ignore_environment_variables and \
           os.environ.get('OTEL_SDK_DISABLED', '').lower().strip() in ['true', 'yes', '1', 'on'] and \
           os.environ.get(self.SKIP_INTERNET_CHECK_NAME, None) is None:
            self._config[self.SKIP_INTERNET_CHECK_NAME] = True

        # Normalize the int values
        for int_name in self._int_value_names:
            if int_name in self._config and isinstance(self._config[int_name], str):
                try:
                    self._config[int_name] = int(self._config[int_name].strip())
                except ValueError:
                    raise ValueError(f"Invalid value for '{int_name}': {self._config[int_name]}")

        self._metric_defs: Dict[str,Configuration._MetricInfo] = {}

    def set_logging_endpoint(self, endpoint: str, auth_token: str = None, cert_ca_file: str = None):
        """
        Sets the logging endpoint. Intended for usage prior to calling initialize_telemetry(). If this method is
        called after the initialize_telemetry() call, it will not work. The change_signal_endpoint must be used.
        If passed in a dict in the constructor, use predefined name LOGGING_ENDPOINT_NAME. If not set,
        the default endpoint will be used.

        Args:
            endpoint (str): Logging endpoint in the form '<IPv4|domain_name>:<port>'.
            auth_token (str): Bearer auth token for the logging endpoint or None.
            cert_ca_file (str): Absolute file path to the private cert file for logging or None. Rarely used.

        Returns:
            Self

        Raises:
            ValueError: If the endpoint format is invalid.
        """
        logging_endpoint = self._Endpoint(endpoint)
        self._config[self.LOGGING_ENDPOINT_NAME] = logging_endpoint.url
        self._endpoints[self.LOGGING_ENDPOINT_NAME] = logging_endpoint
        if auth_token is not None:
            self._config[self.LOGGING_AUTH_TOKEN_NAME] = auth_token
        if cert_ca_file is not None:
            self._config[self.LOGGING_CA_CERT_NAME] = cert_ca_file

        return self

    def set_tracing_endpoint(self, endpoint: str, auth_token: str = None, cert_ca_file: str = None):
        """
        Sets the tracing endpoint. Intended for usage prior to calling initialize_telemetry(). If this method is
        called after the initialize_telemetry() call, it will not work. The change_signal_endpoint must be used.
        If passed in a dict in the constructor, use predefined name TRACING_ENDPOINT_NAME. If not set,
        the default endpoint is used.

        Args:
            endpoint (str): Tracing endpoint in the form '<IPv4|domain_name>:<port>'.
            auth_token (str): Bearer auth token for the tracing endpoint or None.
            cert_ca_file (str): Absolute file path to the private cert file for tracing or None. Rarely used.

        Returns:
            Self

        Raises:
            ValueError: If the endpoint format is invalid.
        """
        tracing_endpoint = self._Endpoint(endpoint)
        self._config[self.TRACING_ENDPOINT_NAME] = tracing_endpoint.url
        self._endpoints[self.TRACING_ENDPOINT_NAME] = tracing_endpoint
        if auth_token is not None:
            self._config[self.TRACING_AUTH_TOKEN_NAME] = auth_token
        if cert_ca_file is not None:
            self._config[self.TRACING_CA_CERT_NAME] = cert_ca_file
        return self

    def set_metrics_endpoint(self, endpoint: str, auth_token: str = None, cert_ca_file: str = None):
        """
        Sets the metrics endpoint. Intended for usage prior to calling initialize_telemetry(). If this method is
        called after the initialize_telemetry() call, it will not work. The change_signal_endpoint must be used.
        If passed in a dict in the constructor, use predefined name METRICS_ENDPOINT_NAME. If not set,
        the default endpoint will be used.

        Args:
            endpoint (str): Metrics endpoint in the form '<IPv4|domain_name>:<port>'.
            auth_token (str): Bearer auth token for the metrics endpoint or None.
            cert_ca_file (str): Absolute file path to the private cert file for metrics or None. Rarely used.

        Returns:
            Self

        Raises:
            ValueError: If the endpoint format is invalid.
        """
        metrics_endpoint = self._Endpoint(endpoint)
        self._config[self.METRICS_ENDPOINT_NAME] = metrics_endpoint.url
        self._endpoints[self.METRICS_ENDPOINT_NAME] = metrics_endpoint
        if auth_token is not None:
            self._config[self.METRICS_AUTH_TOKEN_NAME] = auth_token
        if cert_ca_file is not None:
            self._config[self.METRICS_CA_CERT_NAME] = cert_ca_file
        return self

    def set_console_exporter(self, use_console: bool = True):
        """
        Sets whether to use console exporter for output. If passed in a dict in the constructor, use predefined name
        USE_CONSOLE_EXPORTER_NAME. It applies to all exporters (logging, tracing, metrics). This is a convenience
        used for testing only. Do not set in produiction. Also to set this value without modifying your code use the
        environment variable 'OTEL_USE_CONSOLE_EXPORTER'. Set this to true, yes, or 1. Case doesn't matter.

        $ export OTEL_USE_CONSOLE_EXPORTER=TRUE

        Args:
            use_console (bool): True to use console exporter, False otherwise.

        Returns:
            Self
        """
        self._config[self.USE_CONSOLE_EXPORTER_NAME] = use_console
        return self

    @deprecated
    def set_auth_token(self, auth_token: str):
        """
        Sets the default authentication token for the endpoints (default endpoint). It is a fallback for all endpoints (default, logging,
        tracing, metrics). If passed in a dict in the constructor, use predefined name
        DEFAULT_AUTH_TOKEN_NAME.

        Args:
            auth_token (str): Authentication token to be used with the endpoints.

        Returns:
            Self
        """
        self._config[self.DEFAULT_AUTH_TOKEN_NAME] = auth_token
        return self

    @deprecated
    def set_auth_token_logging(self, auth_token: str):
        """
        Sets the authentication token for the logging endpoint. If passed in a dict in the constructor, use predefined name
        LOGGING_AUTH_TOKEN_NAME.

        Args:
            auth_token (str): Authentication token to be used with the endpoints.

        Returns:
            Self
        """
        self._config[self.LOGGING_AUTH_TOKEN_NAME] = auth_token
        return self

    @deprecated
    def set_auth_token_tracing(self, auth_token: str):
        """
        Sets the authentication token for the tracing endpoint. If passed in a dict in the constructor, use predefined name
        TRACING_AUTH_TOKEN_NAME.

        Args:
            auth_token (str): Authentication token to be used with the endpoints.

        Returns:
            Self
        """
        self._config[self.TRACING_AUTH_TOKEN_NAME] = auth_token
        return self

    @deprecated
    def set_auth_token_metrics(self, auth_token: str):
        """
        Sets the authentication token for the metrics endpoint. If passed in a dict in the constructor, use predefined name
        METRICS_AUTH_TOKEN_NAME.

        Args:
            auth_token (str): Authentication token to be used with the endpoints.

        Returns:
            Self
        """
        self._config[self.METRICS_AUTH_TOKEN_NAME] = auth_token
        return self

    @deprecated
    def set_tls_private_ca_cert(self, cert_file: str):
        """
        TLS certificate used for default endpoint only.
        Sets the actual TLS private CA certificate to be used for secure connections.
        This is used to verify the server's certificate when using TLS. If passed in
        a dict in the constructor, use predefined name DEFAULT_CA_CERT_NAME.
        The caller must pass a file path that will later be utilized to find a cert.
        Can be used to set CA to None is cert_file is None.

        Args:
            cert_file (str): File location of CA cert file intended for use

        Returns:
            Self
        """
        self._config[self.DEFAULT_CA_CERT_NAME] = cert_file
        return self

    @deprecated
    def set_tls_private_ca_cert_logging(self, cert_file: str):
        """
        TLS certificate used for logging endpoint only.
        Sets the actual TLS private CA certificate to be used for secure connections.
        This is used to verify the server's certificate when using TLS. If passed in
        a dict in the constructor, use predefined name LOGGING_CA_CERT_NAME.
        The caller must pass a file path that will later be utilized to find a cert.
        Can be used to set CA to None is cert_file is None.

        Args:
            cert_file (str): File location of CA cert file intended for use

        Returns:
            Self
        """
        self._config[self.LOGGING_CA_CERT_NAME] = cert_file
        return self

    @deprecated
    def set_tls_private_ca_cert_tracing(self, cert_file: str):
        """
        TLS certificate used for tracing endpoint only.
        Sets the actual TLS private CA certificate to be used for secure connections.
        This is used to verify the server's certificate when using TLS. If passed in
        a dict in the constructor, use predefined name TRACING_CA_CERT_NAME.
        The caller must pass a file path that will later be utilized to find a cert.
        Can be used to set CA to None is cert_file is None.

        Args:
            cert_file (str): File location of CA cert file intended for use

        Returns:
            Self
        """
        self._config[self.TRACING_CA_CERT_NAME] = cert_file
        return self

    @deprecated
    def set_tls_private_ca_cert_metrics(self, cert_file: str):
        """
        TLS certificate used for metrics endpoint only.
        Sets the actual TLS private CA certificate to be used for secure connections.
        This is used to verify the server's certificate when using TLS. If passed in
        a dict in the constructor, use predefined name METRICS_CA_CERT_NAME.
        The caller must pass a file path that will later be utilized to find a cert.
        Can be used to set CA to None is cert_file is None.

        Args:
            cert_file (str): File location of CA cert file intended for use

        Returns:
            Self
        """
        self._config[self.METRICS_CA_CERT_NAME] = cert_file
        return self

    def set_logging_level(self, level: str):
        """
        Sets the logging level for the telemetry logging to the collector. The built-in Python
        logging module must be used or logging will not get sent to the server. If passed in a
        dict in the constructor, use predefined name LOGGING_LEVEL_NAME. This will not affect
        the logging level of the root logger, only what is sent to OTel.

        Args:
            level (str): Logging level to be used. It can be 'debug', 'info', 'warn', 'warning', 'error', 'fatal' or 'critical'. If not one of these strings, the logger level is not set.

        Returns:
            Self
        """
        if level not in ['debug', 'info', 'warn', 'warning', 'error', 'fatal', 'critical']:
            return self
        self._config[self.LOGGING_LEVEL_NAME] = level
        return self

    def set_metrics_export_interval_ms(self, interval_ms: int):
        """
        Sets the metrics export interval in milliseconds. If this value is not set,
        the default is 60,000 milliseconds (1 minute). If passed in a dict in the constructor,
        use predefined name METRICS_EXPORT_INTERVAL_NAME. This dictates how long the batching
        inside OpenTelemetry lasts before sending to the collector.

        Args:
            interval (int): Interval in milliseconds for exporting metrics. If this is zero or
            negative then the export interval is not set.

        Returns:
            Self
        """
        if interval_ms <= 0:
            return self
        self._config[self.METRICS_EXPORT_INTERVAL_MS_NAME] = interval_ms
        return self

    def set_tracing_export_interval_ms(self, interval_ms: int):
        """
        Sets the tracing export interval in milliseconds. If this value is not set,
        the default is 60,000 milliseconds (1 minute). If passed in a dict in the constructor,
        use predefined name TRACING_EXPORT_INTERVAL_NAME. This dictates how long the batching
        inside OpenTelemetry lasts before sending to the collector.

        Args:
            interval (int): Interval in milliseconds for exporting metrics. If this is zero or
            negative then the export interval is not set.

        Returns:
            Self
        """
        if interval_ms <= 0:
            return self
        self._config[self.TRACING_EXPORT_INTERVAL_MS_NAME] = interval_ms
        return self

    def set_tracing_session_entropy(self, session_entropy):
        """
        Sets the session entropy for tracing. This is used to ensure that traces are unique
        across different sessions. If this value is not set, a default value will be used. If
        passed in a dict in the constructor, use predefined name SESSION_ENTROPY_VALUE_NAME.

        Args:
            session_entropy (Any): Session entropy to be used for tracing.

        Returns:
            Self
        """
        self._config[self.SESSION_ENTROPY_VALUE_NAME] = session_entropy
        return self

    def set_skip_internet_check(self, value: bool):
        """
        Sets whether to skip the internet check. This is useful for environments that do not have
        internet access. If passed in a dict in the constructor, use predefined name SKIP_INTERNET_CHECK_NAME.

        Args:
            value (bool): True to skip the internet check, False otherwise.

        Returns:
            Self
        """
        self._config[self.SKIP_INTERNET_CHECK_NAME] = value
        return self

    def set_use_cumulative_metrics(self, value: bool):
        """
        Sets the use of cumulative aggregation temporality if True. The default (False) is delta
        (not aggregated).

        Cumulative counters report a measurement consistently for each export interval. The would result in "duplicate"
        metrics. To get metric readings only for the difference between the current count and the previous count, use delta
        aggregation.

        Args:
            value (bool): True turns on cumulative aggregation, False (the default) is to send
            deltas (no aggregation).

        Returns:
            Self
        """
        self._config[self.USE_CUMULATIVE_METRICS_NAME] = value
        return self

    def set_proxy_url(self, proxy_url: str):
        """
        Sets the proxy URL to use for HTTP OTLP exporters. This applies to all HTTP-based
        signal exporters (logging, tracing, metrics). gRPC exporters are not affected.
        If passed in a dict in the constructor, use predefined name PROXY_URL_NAME.
        The environment variable is 'ATEL_PROXY_URL'.

        Args:
            proxy_url (str): The proxy URL (e.g. 'http://proxy.example.com:8080').

        Returns:
            Self
        """
        self._config[self.PROXY_URL_NAME] = proxy_url
        return self

    def set_shutdown_on_exit(self, value: bool):
        """
        Sets whether providers register atexit handlers that flush on interpreter exit.
        If True (default), each provider registers an ``atexit`` handler that flushes on interpreter exit.
        If False, no atexit handlers are registered and the caller becomes responsible for flushing:
        call ``shutdown_telemetry()`` (or ``flush_telemetry()``) before the process exits, otherwise
        buffered telemetry is silently dropped.The environment variable is 'ATEL_SHUTDOWN_ON_EXIT'.

        Args:
            value (bool): True to register atexit handlers, False to manage shutdown manually.

        Returns:
            Self
        """
        self._config[self.SHUTDOWN_ON_EXIT_NAME] = value
        return self

    def set_verbose_export_errors(self, value: bool):
        """
        Sets whether OpenTelemetry export errors are logged to stdout/stderr.
        If False (default), export errors from the OpenTelemetry SDK are suppressed.
        If True, export errors such as "Transient error" will be logged by the OpenTelemetry SDK.
        The environment variable is 'ATEL_VERBOSE_EXPORT_ERRORS'. This will bubble up to global
        OpenTelemetry logging, so make sure to set this to True off if those logs are important, or
        in development.

        Args:
            value (bool): True to show export errors, False to suppress them.

        Returns:
            Self
        """
        self._config[self.VERBOSE_EXPORT_ERRORS_NAME] = value
        return self

    def set_disable_session_id(self, value: bool):
        """
        Sets whether to disable automatic session ID generation.
        If False (default), a session ID is automatically generated and added to telemetry.
        If True, no session ID will be generated or added to telemetry resource attributes.
        The environment variable is 'ATEL_DISABLE_SESSION_ID'.

        Args:
            value (bool): True to disable session ID generation, False to enable it.

        Returns:
            Self
        """
        self._config[self.DISABLE_SESSION_ID_NAME] = value
        return self

    def _get_proxy_url(self) -> str:
        return self._config.get(self.PROXY_URL_NAME, None)

    def _create_proxy_session(self):
        proxy_url = self._get_proxy_url()
        if proxy_url is None:
            return None
        import requests
        session = requests.Session()
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        return session


    class _Endpoint:
        def __init__(self, endpoint: str):
            # Properties:
            # - protocol - protocol of the endpoint passed to the constructor
            # - host - host of the endpoint passed to the constructor
            # - port - port of the endpoint passed to the constructor
            # - path - path of the endpoint passed to the constructor
            # - valid - whether or not the endpoint is valid
            # - _internet_check_port - internet check port used for connection check
            self._parse_endpoint(endpoint.strip())

        # Getters for configuration settings (internal only for the package)
        def _parse_endpoint(self, url: str):
            self._validate_endpoint(url)

            # Default port for internet check
            if self.port is None:
                if self.protocol == 'http':
                    self._internet_check_port = 80
                else:
                    # HTTPS and gRPC(s) use 443 by default
                    self._internet_check_port = 443

            # allow default port usage from user specification
            elif self.port not in (80, 443) and not (1024 <= self.port <= 65535):
                raise ValueError(f"Invalid endpoint format: {url}")
            # Internet check port is user port if one is specified and valid
            else:
                self._internet_check_port = self.port

            # prepare whole url
            url = f"{self.protocol}://{self.host}"
            if self.port:
                url += f":{self.port}"
            url += self.path

            self.url = url

        def _validate_endpoint(self, endpoint: str):
            if endpoint == '':
                raise ValueError(f"Invalid endpoint format: {endpoint}")
            pattern = re.compile(
                r"^"
                r"(https?://|grpcs?://)"                       # capture group 1: optional protocol
                r"("                                           # capture group 2: host
                    r"(?!0\.)"                                 # Disallow IPs starting with 0.
                    r"(?:\d{1,3}\.){3}\d{1,3}"                 # IPv4 format (non-capturing group)
                    r"|"
                    r"(?:[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*"       # domain segment
                    r"(?:\.[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*)*)"  # more segments
                r")"
                r"(?::(\d{1,5}))?"                             # capture group 3: optional port
                r"(/.*)?$"                                     # capture group 4: optional path
            )

            match = pattern.match(endpoint)
            if not match:
                raise ValueError(f"Invalid endpoint format: {endpoint}")

            protocol_str = match.group(1)
            self.host = match.group(2)
            port = match.group(3)
            self.port = int(port) if port is not None else None
            self.path = match.group(4) or ""

            # Extract protocol
            self.protocol = protocol_str.rstrip('://')
            # Determine tls
            self.tls = True if self.protocol[-1] == 's' else False

            # If it's an IP, validate each octet
            if re.match(r"^(\d{1,3}\.)+\d{1,3}$", self.host):
                quads = list(map(int, self.host.split('.')))
                if len(quads) != 4:
                    raise ValueError(f"Invalid endpoint format: {endpoint}")
                if quads[0] == 0 or quads[0] == 255 or quads[3] == 0 or quads[3] == 255:
                    raise ValueError(f"Invalid endpoint format: {endpoint}")
                for q in quads:
                    if q > 255:
                        raise ValueError(f"Invalid endpoint format: {endpoint}")

    def _change_signal_endpoint(self, signal: str, new_endpoint: str, auth_token: str=None):
        set_endpoint = getattr(self, f"set_{signal}_endpoint", None)
        set_endpoint(new_endpoint, auth_token=auth_token)
        get_endpoint = getattr(self, f"_get_{signal}_endpoint", None)
        return get_endpoint()

    def _set_otel_signal_endpoint(self, endpoint: str, signal: str) -> str:
        if endpoint.lower().startswith("grpc"):
            return endpoint
        endpoint_str = f"v1/{signal}"
        if not endpoint.endswith(endpoint_str):
            endpoint_str = "/" + endpoint_str if endpoint[-1] != "/" else endpoint_str
            return endpoint + endpoint_str
        else:
            return endpoint

    def _get_default_endpoint(self) -> str:
        return self._config.get(self.DEFAULT_ENDPOINT_NAME, '')

    def _get_logging_endpoint(self) -> str:
        endpoint = self._config.get(self.LOGGING_ENDPOINT_NAME, self._get_default_endpoint())
        return self._set_otel_signal_endpoint(endpoint, "logs")

    def _get_tracing_endpoint(self) -> str:
        endpoint = self._config.get(self.TRACING_ENDPOINT_NAME, self._get_default_endpoint())
        return self._set_otel_signal_endpoint(endpoint, "traces")

    def _get_metrics_endpoint(self) -> str:
        endpoint = self._config.get(self.METRICS_ENDPOINT_NAME, self._get_default_endpoint())
        return self._set_otel_signal_endpoint(endpoint, "metrics")

    def _prepare_ca_cert(self, protocol: str, cert_file: str) -> str:
        if protocol in ['http', 'https']:
            return cert_file  # just return cert file for HTTP exporter ca_cert
        else:
            if cert_file:
                with open(cert_file, 'rb') as f:
                    ca_cert_bytes = f.read()  # gRPC exporter requires a bytes string
                creds = grpc.ssl_channel_credentials(root_certificates=ca_cert_bytes)
                return creds
            else:
                # Use system trust store (for public CAs)
                creds = grpc.ssl_channel_credentials()
                return creds

    def _get_ca_cert_default(self) -> str:
        cert_file = self._config.get(self.DEFAULT_CA_CERT_NAME, None)
        return self._prepare_ca_cert(self._get_request_protocol_default().protocol, cert_file)

    def _get_ca_cert_logging(self) -> str:
        cert_file = self._config.get(self.LOGGING_CA_CERT_NAME, self._get_ca_cert_default())
        return self._prepare_ca_cert(self._get_request_protocol_logging(), cert_file)

    def _get_ca_cert_tracing(self) -> str:
        cert_file = self._config.get(self.TRACING_CA_CERT_NAME, self._get_ca_cert_default())
        return self._prepare_ca_cert(self._get_request_protocol_tracing(), cert_file)

    def _get_ca_cert_metrics(self) -> str:
        cert_file = self._config.get(self.METRICS_CA_CERT_NAME, self._get_ca_cert_default())
        return self._prepare_ca_cert(self._get_request_protocol_metrics(), cert_file)

    def _get_console_exporter(self) -> bool:
        return self._config.get(self.USE_CONSOLE_EXPORTER_NAME, False)

    def _get_auth_token_default(self) -> str:
        return self._config.get(self.DEFAULT_AUTH_TOKEN_NAME, None)

    def _get_auth_token_logging(self) -> str:
        return self._config.get(self.LOGGING_AUTH_TOKEN_NAME, self._get_auth_token_default())

    def _get_auth_token_tracing(self) -> str:
        return self._config.get(self.TRACING_AUTH_TOKEN_NAME, self._get_auth_token_default())

    def _get_auth_token_metrics(self) -> str:
        return self._config.get(self.METRICS_AUTH_TOKEN_NAME, self._get_auth_token_default())

    def _get_logging_level(self) -> str:
        return self._config.get(self.LOGGING_LEVEL_NAME, 'warning')

    def _get_metrics_export_interval_ms(self) -> int:
        return self._config.get(self.METRICS_EXPORT_INTERVAL_MS_NAME, 60_000)

    def _get_tracing_export_interval_ms(self) -> int:
        return self._config.get(self.TRACING_EXPORT_INTERVAL_MS_NAME, 60_000)

    def _get_tracing_session_entropy(self):
        if self._config.get(self.SESSION_ENTROPY_VALUE_NAME, None) is None:
            import time
            self._config[self.SESSION_ENTROPY_VALUE_NAME] = int(time.time() * 1e9)
        return self._config.get(self.SESSION_ENTROPY_VALUE_NAME)

    def _get_skip_internet_check(self) -> bool:
        return self._config.get(self.SKIP_INTERNET_CHECK_NAME, False)

    def _get_TLS_default(self) -> bool:
        # will raise if there is no default tls (means there is no default endpoint)
        return self._endpoints[self.DEFAULT_ENDPOINT_NAME]

    def _get_TLS_logging(self) -> str:
        return self._endpoints.get(self.LOGGING_ENDPOINT_NAME, self._get_TLS_default()).tls

    def _get_TLS_metrics(self) -> str:
        return self._endpoints.get(self.METRICS_ENDPOINT_NAME, self._get_TLS_default()).tls

    def _get_TLS_tracing(self) -> str:
        return self._endpoints.get(self.TRACING_ENDPOINT_NAME, self._get_TLS_default()).tls

    def _get_request_protocol_default(self) -> str:
        # will raise if there is no default protocol (means there is no default endpoint)
        return self._endpoints[self.DEFAULT_ENDPOINT_NAME]

    def _get_request_protocol_logging(self) -> str:
        return self._endpoints.get(self.LOGGING_ENDPOINT_NAME, self._get_request_protocol_default()).protocol

    def _get_request_protocol_metrics(self) -> str:
        return self._endpoints.get(self.METRICS_ENDPOINT_NAME, self._get_request_protocol_default()).protocol

    def _get_request_protocol_tracing(self) -> str:
        return self._endpoints.get(self.TRACING_ENDPOINT_NAME, self._get_request_protocol_default()).protocol

    def _get_use_cumulative_metrics(self) -> bool:
        return self._config.get(self.USE_CUMULATIVE_METRICS_NAME, False)

    def _get_shutdown_on_exit(self) -> bool:
        return self._config.get(self.SHUTDOWN_ON_EXIT_NAME, True)

    def _get_verbose_export_errors(self) -> bool:
        return self._config.get(self.VERBOSE_EXPORT_ERRORS_NAME, False)

    def _get_disable_session_id(self) -> bool:
        return self._config.get(self.DISABLE_SESSION_ID_NAME, False)
