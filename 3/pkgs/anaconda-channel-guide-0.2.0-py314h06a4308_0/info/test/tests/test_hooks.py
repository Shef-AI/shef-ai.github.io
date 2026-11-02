from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.exceptions import PackagesNotFoundInChannelsError
from conda.plugins.types import CondaExceptionEvent

from anaconda_channel_guide.box import ChannelGuideBox
from anaconda_channel_guide.hooks import conda_error_hints, conda_settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def make_pnfe_event(
    json: bool = False,
    channels: tuple[str, ...] | None = ("defaults",),
    packages: list[str] | None = None,
    offline: bool = False,
) -> CondaExceptionEvent:
    """Build a CondaExceptionEvent for PackagesNotFoundError hook tests."""
    channel_urls = () if channels is None else channels
    exc = PackagesNotFoundInChannelsError(packages or ["pychoir"], channel_urls=channel_urls)
    return CondaExceptionEvent(
        exc_type=PackagesNotFoundInChannelsError,
        exc_value=exc,
        exc_traceback=None,
        channels=channels,
        json=json,
        offline=offline,
    )


def test_conda_settings() -> None:
    """
    Ensure the correct conda settings are returned
    """
    settings = list(conda_settings())

    assert len(settings) == 1
    assert settings[0].name == "anaconda_channel_guide"
    assert settings[0].description == "Whether Anaconda Channel Guide is enabled"
    assert settings[0].parameter.default.value is True


@pytest.mark.parametrize(
    "enabled",
    [pytest.param(True, id="enabled"), pytest.param(False, id="disabled")],
)
def test_enable_disable_plugin(enabled: bool, mocker: MockerFixture) -> None:
    """
    Make sure that no hint is yielded when the plugin is disabled via settings
    """
    mocker.patch("anaconda_channel_guide.hooks.context.plugins.anaconda_channel_guide", enabled)
    event = make_pnfe_event()
    mock_handle = mocker.patch("anaconda_channel_guide.hooks.handle_pnfe", return_value=None)

    hints = list(conda_error_hints(event.exc_value))

    assert mock_handle.called is enabled
    assert hints == []


@pytest.mark.parametrize(
    ("authenticated", "main_x_configured", "expected_fragments"),
    [
        pytest.param(
            False,
            False,
            ["$ anaconda login", "conda config --append default_channels"],
            id="needs_login_and_config",
        ),
        pytest.param(False, True, ["$ anaconda login"], id="needs_login_only"),
        pytest.param(
            True, False, ["conda config --append default_channels"], id="needs_config_only"
        ),
    ],
)
def test_box_correct_steps_appended(
    mocker: MockerFixture,
    authenticated: bool,
    main_x_configured: bool,
    expected_fragments: list[str],
) -> None:
    """Plugin enabled, normal output, package on main-x, action still needed."""
    event = make_pnfe_event()

    mocker.patch(
        "anaconda_channel_guide.hooks.context.plugins.anaconda_channel_guide",
        True,
    )
    mocker.patch(
        "anaconda_channel_guide.hooks.is_logged_in",
        return_value=authenticated,
    )
    mocker.patch(
        "anaconda_channel_guide.hooks.is_main_x_configured",
        return_value=main_x_configured,
    )
    mocker.patch(
        "anaconda_channel_guide.plugin.is_available_on_main_x",
        return_value=True,
    )

    hints = list(conda_error_hints(event.exc_value))

    assert len(hints) == 1
    assert hints[0].hint_code == "anaconda_channel_guide"
    assert ChannelGuideBox.TITLE in hints[0].text
    for fragment in expected_fragments:
        assert fragment in hints[0].text


@pytest.mark.parametrize(
    ("enabled", "authenticated", "main_x_configured", "on_main_x"),
    [
        pytest.param(True, True, True, True, id="no_action_needed"),
        pytest.param(True, False, False, False, id="not_on_main_x"),
        pytest.param(False, False, False, True, id="disabled"),
    ],
)
def test_box_not_appended(
    mocker: MockerFixture,
    enabled: bool,
    authenticated: bool,
    main_x_configured: bool,
    on_main_x: bool,
) -> None:
    """Box is not appended when plugin disabled or user state makes it unnecessary."""
    event = make_pnfe_event()
    mocker.patch(
        "anaconda_channel_guide.hooks.context.plugins.anaconda_channel_guide",
        enabled,
    )
    mocker.patch(
        "anaconda_channel_guide.hooks.is_logged_in",
        return_value=authenticated,
    )
    mocker.patch(
        "anaconda_channel_guide.hooks.is_main_x_configured",
        return_value=main_x_configured,
    )
    mocker.patch(
        "anaconda_channel_guide.plugin.is_available_on_main_x",
        return_value=on_main_x,
    )
    hints = list(conda_error_hints(event.exc_value))
    assert hints == []
