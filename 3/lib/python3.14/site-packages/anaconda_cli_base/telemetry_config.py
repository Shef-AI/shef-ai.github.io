import os
from typing import Optional, Any

from pydantic import field_validator, Field

from anaconda_cli_base.config import AnacondaBaseSettings

AUTHENTICATED_ENDPOINT = "https://metrics.aa.anaconda.com"
PUBLIC_ENDPOINT = "https://public.telemetry.anaconda.com"


class TelemetryConfig(AnacondaBaseSettings, table_name="telemetry"):
    """Telemetry configuration.

    Reads from [telemetry] in ~/.anaconda/config.toml.
    Environment variables use ANACONDA_TELEMETRY_ prefix.
    """

    enabled: bool = Field(default=True, validate_default=True)
    endpoint: Optional[str] = None
    share_session_identity: bool = True
    proxy_url: Optional[str] = None
    flush_timeout_ms: int = 500
    export_interval_ms: int = 60000

    @field_validator("enabled", mode="before")
    @classmethod
    def _check_disabled(cls, v: Any) -> Any:
        if os.environ.get("OTEL_SDK_DISABLED", "").lower() in ("true", "1", "yes"):
            # Checking for this env var ensures we don't load all the modules just
            # to have them disabled anyway
            return False
        return v
