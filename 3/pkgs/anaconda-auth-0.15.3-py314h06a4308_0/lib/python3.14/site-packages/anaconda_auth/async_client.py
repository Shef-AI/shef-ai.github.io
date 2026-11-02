from functools import cached_property
from typing import Any

import httpx

from anaconda_auth.client import BaseClient


# add BaseClient superclass to pick up properties
class AsyncBaseClient(httpx.AsyncClient, BaseClient):  # type: ignore
    """Version of client.BaseClient for use in async contexts."""

    def __init__(
        self, httpx_kwargs: dict[str, Any] | None = None, **kwargs: dict[str, Any]
    ) -> None:
        """
        httpx_kwargs: passed to HTTPX. Cannot include the keys derived
           from the sync client: headers, verify, cert, base_url and auth.
        kwargs: passed to BaseClient and its requests.Session superclass
        """
        self._sync_client = BaseClient(**kwargs)  # type: ignore
        self.config = self._sync_client.config
        self.api_version = self._sync_client.api_version

        super().__init__(
            headers=self._sync_client.headers,  # type: ignore
            verify=self._sync_client._ssl,  # type: ignore
            cert=self._sync_client.config.client_cert,
            base_url=self._sync_client._base_uri,
            auth=self._sync_client.auth,  # type: ignore
            **(httpx_kwargs or {}),
        )

    @cached_property
    def account(self) -> dict:
        return self._sync_client.account

    async def request(  # type: ignore
        self,
        method: str,  # type: ignore
        url: str,  # type: ignore
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        kwargs["timeout"] = 600
        response = await super().request(method, url, *args, **kwargs)

        min_api_version_string = response.headers.get("Min-Api-Version")
        self._validate_api_version(min_api_version_string)

        return response
