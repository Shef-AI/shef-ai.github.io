# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Low-level remote (the "raw" endpoint JSON) Terms of Service metadata management."""

from __future__ import annotations

from datetime import datetime
from json import JSONDecodeError
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.url import join_url
from conda.gateways.connection.session import get_session
from conda.models.channel import Channel
from pydantic import ValidationError
from requests.exceptions import RequestException

from .exceptions import (
    CondaToSInvalidError,
    CondaToSMissingError,
    CondaToSPermissionError,
)
from .models import RemoteToSMetadata
from .path import get_cache_path

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from requests import Response

ENDPOINT: Final = "terms.json"


def get_endpoint(channel: str | Channel) -> Response:
    """Get the metadata endpoint for the given channel."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError(
            "`channel` must have a base URL. "
            "(hint: `conda.models.channel.MultiChannel` doesn't have an endpoint)"
        )

    session = get_session(channel.base_url)
    url = join_url(channel.base_url, ENDPOINT)

    saved_token_setting = context.add_anaconda_token
    try:
        # do not inject conda/binstar token into URL for two reasons:
        # 1. Metadata endpoint shouldn't be a protected endpoint
        # 2. CondaHttpAuth.add_binstar_token adds subdir to the URL
        #    which the metadata endpoint doesn't have
        context.add_anaconda_token = False
        response = session.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=(
                context.remote_connect_timeout_secs,
                context.remote_read_timeout_secs,
            ),
        )
        response.raise_for_status()
    except RequestException as exc:
        # RequestException: failed to get metadata endpoint
        raise CondaToSMissingError(channel) from exc
    finally:
        context.add_anaconda_token = saved_token_setting
    return response


def get_cached_endpoint(
    channel: str | Channel,
    *,
    cache_timeout: int | float | None = float("inf"),
) -> Path | None:
    """Get the path to cached payload for the given channel."""
    # early exit if cache is disabled
    if not cache_timeout:
        return None

    # argument validation/coercion
    path = get_cache_path(channel)
    if not isinstance(cache_timeout, int | float):
        raise TypeError("`cache_timeout` must be an integer, float, or falsy.")

    # get mtime of cache
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        # FileNotFoundError: cache path doesn't exist
        return None

    # check if cache is stale
    now = datetime.now().timestamp()  # noqa: DTZ005
    if (now - mtime) >= cache_timeout:
        return None
    return path


def write_cached_endpoint(
    channel: str | Channel,
    metadata: RemoteToSMetadata | None,
) -> Path:
    """Write the metadata cache for the given channel."""
    # argument validation/coercion
    path = get_cache_path(channel)
    if metadata and not isinstance(metadata, RemoteToSMetadata):
        raise TypeError("`metadata` must be a RemoteToSMetadata.")

    # write to cache
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if metadata:
            path.write_text(metadata.model_dump_json())
        else:
            path.touch()
    except PermissionError as exc:
        # PermissionError: can't write to cache path
        raise CondaToSPermissionError(path, channel) from exc

    return path


def get_remote_metadata(  # noqa: C901
    channel: str | Channel,
    *,
    cache_timeout: int | float | None = None,
) -> RemoteToSMetadata:
    """Get the metadata metadata for the given channel."""
    # argument validation/coercion
    cache = get_cached_endpoint(
        channel,
        # when in offline mode cache_timeout is ignored
        cache_timeout=float("inf") if context.offline else cache_timeout,
    )

    # return cached metadata
    if cache:
        try:
            text = cache.read_text().strip()
            if not text:
                raise CondaToSMissingError(channel)
        except FileNotFoundError as exc:
            # FileNotFoundError: cache path doesn't exist
            raise CondaToSMissingError(channel) from exc
        except PermissionError as exc:
            # PermissionError: can't read cache path
            raise CondaToSPermissionError(cache, channel) from exc

        try:
            return RemoteToSMetadata.model_validate_json(text)
        except ValidationError as exc:
            # ValidationError: invalid JSON schema
            raise CondaToSInvalidError(channel) from exc

    # return remote metadata
    try:
        metadata = RemoteToSMetadata(**get_endpoint(channel).json())
    except CondaToSMissingError:
        # CondaToSMissingError: no Terms of Service for this channel
        # create an empty cache to prevent repeated requests
        write_cached_endpoint(channel, None)
        raise
    except RuntimeError as exc:
        # RuntimeError: potentially raised by CondaSession due to --offline
        if "offline mode" in exc.args[0]:
            write_cached_endpoint(channel, None)
            raise CondaToSMissingError(channel) from exc
        raise
    except (AttributeError, TypeError, JSONDecodeError, ValidationError) as exc:
        # AttributeError: response has no JSON
        # TypeError: invalid JSON
        # JSONDecodeError: invalid JSON
        # ValidationError: invalid JSON schema
        write_cached_endpoint(channel, None)
        raise CondaToSInvalidError(channel) from exc
    else:
        write_cached_endpoint(channel, metadata)
        return metadata
