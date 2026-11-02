import logging
from typing import Optional
from typing import Union

from anaconda_auth.client import BaseClient

logger = logging.getLogger(__name__)


def fetch_org_features(ssl_verify: Optional[Union[bool, str]] = None) -> Optional[list]:
    """Fetch organization features from userinfo."""
    try:
        kwargs = {}
        if ssl_verify is not None:
            kwargs["ssl_verify"] = ssl_verify
        client = BaseClient(**kwargs)  # type: ignore
        resp = client.get("/api/auth/oauth2/userinfo")
        resp.raise_for_status()
        return resp.json().get("organization_features") or []
    except Exception:
        return None


def check_client_token_status(token: str) -> bool:
    """Check if a client token is already mapped to a user.

    Uses the read-only client-token-status endpoint.  A 200 response means
    the token is already registered; any other outcome is treated as
    "not registered".
    """
    try:
        client = BaseClient()
        resp = client.get(
            "/api/environments/client-token-status",
            params={"client_token": token},
        )
        return resp.status_code == 200
    except Exception:
        return False


def get_orgs_with_env_logger(org_features: list) -> list[str]:
    """Return org names that have the env_logger feature enabled.

    Returns an empty list for community users since they do not
    belong to any organization with the environments feature.
    """
    return [
        org["org"] for org in org_features if "environments" in org.get("features", [])
    ]
