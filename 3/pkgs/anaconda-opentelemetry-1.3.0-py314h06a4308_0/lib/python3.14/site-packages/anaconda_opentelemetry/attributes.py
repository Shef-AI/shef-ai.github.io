# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# attributes.py

import hashlib, json, logging, platform, re
from typing import Dict, Tuple, Literal, List
from dataclasses import dataclass, field, fields, InitVar
from .__version__ import __SDK_VERSION__, __TELEMETRY_SCHEMA_VERSION__

try:
    from anaconda_anon_usage import tokens
    # map token funcs to otel resource attribute names
    TOKEN_FUNCS = [
        ("aau.version", tokens.version_token),
        ("aau.client.token", tokens.client_token),
        ("aau.session.token", tokens.session_token),
        ("aau.environment.token", tokens.environment_token),
        ("aau.organization.tokens", tokens.organization_tokens),
        ("aau.installer.tokens", tokens.installer_tokens),
        ("aau.machine.tokens", tokens.machine_tokens),
        ("aau.anaconda_auth.token", tokens.anaconda_auth_token),
    ]
except ImportError:
    TOKEN_FUNCS = []


@dataclass
class ResourceAttributes:
    """
    Class used to configure common attributes on initialization and dynamic attributes thereafter

    Parameters:
        service_name (str): name of client service. REQUIRED (enforced regex of ^[a-zA-Z0-9._-]{1,30}$), converted later to service.name
        service_version (str): version of client service. REQUIRED (enforced regex of ^[a-zA-Z0-9._-]{1,30}$), converted later to service.version
        os_type (str): operating system type of client machine
        os_version (str): operating system version of client machine
        python_version (str): python version of client the package
        hostname (str): hostname of client machine
        platform (str): infrastructure on which the software is provided
        environment (Literal["", "test", "development", "staging", "production"]): envrionment the software is running in
        user_id (str): some string denoting a user of a client application.
                       This will not be stored in Resource Attributes and will be moved to attributes.
        auto_collect (bool): if True (default), automatically collects os_type, os_version, python_version, and hostname when not provided
        exclude_auto_collect (List[str]): list of attribute names to exclude from auto-collection. Valid values: "os_type", "os_version", "python_version", "hostname"
        anon_usage (bool): if True, collects anonymous usage tokens from anaconda-anon-usage package
        parameters (Dict[str, str]): optional dictionary containing all other telemetry attributes a client would like to add
        client_sdk_version (str): version of package. READONLY
        schema_version (str): version of telemetry schema used by package. READONLY
    """
    # settable
    service_name: str
    service_version: str
    os_type: str = field(
        default="",
        metadata={"otel_name": "os.type", "auto_collect": True}
    )
    os_version: str = field(
        default="",
        metadata={"otel_name": "os.version", "auto_collect": True}
    )
    python_version: str = field(
        default="",
        metadata={"otel_name": "python.version", "auto_collect": True}
    )
    hostname: str = field(
        default="",
        metadata={"otel_name": "hostname", "hash": True, "auto_collect": True}
    )
    platform: str = field(
        default="",
        metadata={"otel_name": "platform"}
    )
    environment: Literal["", "test", "development", "staging", "production"] = field(
        default="",
        metadata={"otel_name": "environment"}
    )
    user_id: str = field(
        default=""
    )
    auto_collect: InitVar[bool] = True
    exclude_auto_collect: InitVar[List[str]] = None
    anon_usage: InitVar[bool] = False
    # Readonly
    client_sdk_version: str = field(
        default=__SDK_VERSION__,
        init=False,
        metadata={"readonly": True, "otel_name": "client.sdk.version"}
    )
    schema_version: str = field(
        default=__TELEMETRY_SCHEMA_VERSION__,
        init=False,
        metadata={"readonly": True, "otel_name": "schema.version"}
    )
    parameters: dict = field(
        default_factory=dict,
        init=False,
        metadata={"readonly": True, "otel_name": "parameters"}
    )

    def __setattr__(self, key, value):
        is_aau_key = isinstance(key, str) and key.startswith("aau.")
        if value is None or key is None:
            if not is_aau_key:
                logging.getLogger(__package__).warning(f"Either an attribute or key is None which is not allowed. Attribute: `{key}`. Value: `{value}`")
        elif hasattr(self, '_readonly_fields') and key in self._readonly_fields:
            logging.getLogger(__package__).warning(f"Attempted overwrite of readonly common attribute {key}")
        elif (key == "service_name" or key == "service_version") and not self._check_valid_string(value):
            raise ValueError(f"{key} not set. {value} is invalid regex for this key: `^[a-zA-Z0-9._-]{{1,30}}$`. This is a required parameter")
        else:
            processed_value = value if key == "parameters" else (json.dumps(value) if isinstance(value, (list, dict)) else str(value))
            # check if this attribute should be hashed
            if processed_value:
                for f in fields(self):
                    if f.name == key and f.metadata.get("hash", False) is True:
                        processed_value = hashlib.sha256(processed_value.encode("utf-8")).hexdigest()
                        break
            super().__setattr__(str(key), processed_value)

    def __post_init__(self, auto_collect: bool, exclude_auto_collect: List[str], anon_usage: bool):
        # set non-init readonly
        self.client_sdk_version = __SDK_VERSION__
        self.schema_version = __TELEMETRY_SCHEMA_VERSION__
        self._readonly_fields = {
            f.name for f in fields(self)
            if f.metadata.get("readonly", False) is True
        }
        self._auto_collect_fields = {
            f.name for f in fields(self)
            if f.metadata.get("auto_collect", False) is True
        }
        # default certain attribute values if needed (only if auto_collect is enabled)
        if auto_collect:
            exclude_set = set(exclude_auto_collect or [])
            if not self.os_type or not self.os_version:
                if "os_type" not in exclude_set and "os_version" not in exclude_set:
                    self.os_type, self.os_version = self._get_os_info()
                elif "os_type" not in exclude_set:
                    self.os_type = self._get_os_info()[0]
                elif "os_version" not in exclude_set:
                    self.os_version = self._get_os_info()[1]
            if not self.python_version and "python_version" not in exclude_set:
                self.python_version = platform.python_version()
            if not self.hostname and "hostname" not in exclude_set:
                self.hostname = self._get_host_name()

        # if anon-usage is specified
        if anon_usage:
            for name, func in TOKEN_FUNCS:
                self.__setattr__(name, func())

        # check for valid environment
        valid_environments = {"", "test", "development", "staging", "production"}

        # enforce lowercase
        self.environment = self.environment.strip().lower()
        if self.environment not in valid_environments:
            logging.getLogger(__package__).warning(f"Invalid environment value `{self.environment}`, setting to empty string. Envrionment must be in {valid_environments}")
            self.environment = ""

    def _get_os_info(self) -> Tuple[str, str]:
        """Get system OS type and version"""
        return platform.system(), platform.release()

    def _get_host_name(self) -> str:
        """Get the hostname of the machine"""
        from socket import gethostname
        return gethostname()

    def _check_valid_string(self, value) -> bool:
        """Check that service_name and service_version match valid regex"""
        if re.match(r"^[a-zA-Z0-9._-]{1,30}$", str(value)):
            return True
        return False

    def _get_attributes(self) -> Dict[str, str]:
        """Convert all attributes to a dictionary, omitting auto-collected attributes when empty"""
        return {
            k: v for k, v in self.__dict__.items()
            if k not in ('_readonly_fields', '_auto_collect_fields') and not (k in self._auto_collect_fields and v == '')
        }

    def set_attributes(self, **kwargs) -> None:
        """
        Sets attributes according to key value pairs passed to this function. Will overwrite existing attributes, unless they are readonly.

        Note: Setting user_id via this method is maintained for backwards compatability. Doing so will override any user_ids set later in event specific attributes.

        Parameters:
            \\*\\*kwargs: any keyword arguments. This can set named class properties (common attributes), or any other wildcard name (stored in `parameters`)
        The following are the common attributes that can be set:
            service_name (str): name of client service\n
            service_version (str): version of client service\n
            os_type (str): operating system type of client machine\n
            os_version (str): operating system version of client machine\n
            python_version (str): python version of client the package\n
            hostname (str): hostname of client machine\n
            platform (str): infrastructure on which the software runs\n
            environment (Literal["", "test", "development", "staging", "production"]): environment of the software\n
            user_id (str): some string denoting a user of a client application\n
        """
        for kwarg in kwargs:
            # if kwarg has already been initialized as a property
            if kwarg in self.__dict__.keys():
                self.__setattr__(kwarg, kwargs[kwarg])
            else:
                self.parameters[str(kwarg)] = str(kwargs[kwarg])

        return self