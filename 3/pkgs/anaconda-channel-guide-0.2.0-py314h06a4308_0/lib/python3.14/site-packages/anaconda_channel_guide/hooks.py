from __future__ import annotations

from typing import TYPE_CHECKING

from conda import plugins
from conda.base.context import context
from conda.common.configuration import PrimitiveParameter
from conda.exceptions import PackagesNotFoundError
from conda.plugins import hookimpl
from conda.plugins.types import (
    CondaPreCommand,
    CondaSetting,
)

from anaconda_channel_guide.plugin import handle_pnfe, is_logged_in, is_main_x_configured
from anaconda_channel_guide.prefetch import prefetch_main_x_repodata

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from conda.plugins.types import CondaErrorHint

    from anaconda_channel_guide.box import ChannelGuideBox


def _channel_guide_result(error: PackagesNotFoundError) -> ChannelGuideBox | None:
    if not context.plugins.anaconda_channel_guide:
        return None

    if context.offline:
        return None

    if context.json:
        return None

    main_x_configured = is_main_x_configured(context.channels)
    missing_packages = list(error.packages)
    authenticated = is_logged_in()

    return handle_pnfe(missing_packages, main_x_configured, authenticated, subdirs=context.subdirs)


@plugins.hookimpl()
def conda_error_hints(error: Exception) -> Iterator[CondaErrorHint]:
    """Contribute channel-guide remediation as structured conda error hints."""

    if not isinstance(error, PackagesNotFoundError) or not error.channel_urls:
        return

    result = _channel_guide_result(error)
    if result:
        yield plugins.types.CondaErrorHint(
            text=result.plain_text_message(),
            hint_code="anaconda_channel_guide",
        )


@hookimpl
def conda_pre_commands() -> Iterable[CondaPreCommand]:
    yield CondaPreCommand(
        name="channel-guide-main-x-prefetch",
        action=prefetch_main_x_repodata,
        run_for={"create", "env_create", "env_update", "install", "search"},
    )


@hookimpl
def conda_settings() -> Iterator[CondaSetting]:
    """Return a list of settings that can be configured by the user."""
    yield CondaSetting(
        name="anaconda_channel_guide",
        description="Whether Anaconda Channel Guide is enabled",
        parameter=PrimitiveParameter(True, element_type=bool),
    )
