from __future__ import annotations

from typing import TYPE_CHECKING

from anaconda_auth.token import TokenInfo, TokenNotFoundError
from conda.base.context import context
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

from anaconda_channel_guide.box import (
    CONFIG_STEP,
    LOGIN_STEP,
    ChannelGuideBox,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


MAIN_X_CHANNEL_URL = "https://repo.anaconda.cloud/repo/main-x"
MAIN_X_CHANNEL_NAME = Channel.from_url(MAIN_X_CHANNEL_URL).canonical_name


def is_logged_in() -> bool:
    """Checks if the user is authenticated via anaconda-auth.

    Attempts to load the token. Returns False if no token
    is found or if the token has expired.

    :returns: True if the user has a valid (non-expired) token, False otherwise
    """
    try:
        token_info = TokenInfo.load()
        return not token_info.expired
    except TokenNotFoundError:
        return False


def is_main_x_configured(channels: Iterable[str]) -> bool:
    """Checks if the main-x channel is configured in the user's conda setup.

    :param channels: Channel names or URLs active for the current command
    :returns: True if main-x is in the configured channels, False otherwise
    """
    return any(is_main_x_channel(channel) for channel in (channels or ()))


def is_main_x_channel(channel: str) -> bool:
    try:
        return Channel(channel).canonical_name == MAIN_X_CHANNEL_NAME
    except Exception:
        return False


def is_available_on_main_x(
    packages: Iterable[MatchSpec | PackageRecord | str],
    subdirs: Iterable[str],
) -> bool:
    """Checks whether all of the given packages are available on the main-x channel.

    Normalizes package specs before querying: version constraints are stripped
    so we check by name only, and specs pinned to a non-main-x channel are
    rejected immediately.

    :param packages: Package specs to check (names, match specs, or records)
    :returns: True if every package is available on main-x, False otherwise
    """
    try:
        specs = []
        for package in packages:
            # Solvers typically convert into MatchSpec, but exception events
            # also allow for PackageRecord. These are unlikely to come from
            # a channel search, so we return to be defensive.
            if isinstance(package, PackageRecord):
                return False
            spec = MatchSpec(package) if isinstance(package, str) else package
            if spec.get_exact_value("channel") is not None:
                return False
            specs.append(spec)

        # Temporary workaround until main/main-x can serve this via sharded repodata.
        # Avoid refreshing unsharded repodata on the exception path.
        with context._override("use_index_cache", True):
            for spec in specs:
                if not SubdirData.query_all(spec, channels=[MAIN_X_CHANNEL_URL], subdirs=subdirs):
                    return False

    except Exception:
        return False
    return True


def handle_pnfe(
    missing_packages: list[str | MatchSpec | PackageRecord],
    main_x_configured: bool,
    authenticated: bool,
    subdirs: Iterable[str],
) -> ChannelGuideBox | None:
    """Handles a PackageNotFoundError by checking if missing packages
    are available on main-x and guiding the user on what to do next.

    :param missing_packages: List of package names that triggered the PNFE
    :param main_x_configured: True if the main-x channel is already in the user's config
    :param authenticated: True if the user is currently logged in
    :param subdirs: List of subdirectories to check for availability
    :returns: A ChannelGuideBox object if action is needed,
        None to fall through to default PNFE behavior
    """
    if not missing_packages:
        return None

    if authenticated and main_x_configured:
        return None

    if not is_available_on_main_x(missing_packages, subdirs):
        return None

    steps = []
    if not authenticated:
        steps.append(LOGIN_STEP)
    if not main_x_configured:
        steps.append(CONFIG_STEP)
    return ChannelGuideBox(missing_packages, steps)
