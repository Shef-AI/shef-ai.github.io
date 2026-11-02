from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from anaconda_auth.token import TokenNotFoundError
from conda.base.context import context
from conda.exceptions import PackagesNotFoundInChannelsError
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

from anaconda_channel_guide.box import ChannelGuideBox
from anaconda_channel_guide.hooks import conda_error_hints
from anaconda_channel_guide.plugin import (
    MAIN_X_CHANNEL_NAME,
    MAIN_X_CHANNEL_URL,
    handle_pnfe,
    is_available_on_main_x,
    is_logged_in,
    is_main_x_configured,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest_mock import MockerFixture

LOGIN_CMD = "anaconda login"
CONFIG_CMD = "conda config --append default_channels https://repo.anaconda.cloud/repo/main-x"
SUBDIRS = ("linux-64", "noarch")

PYCHOIR_RECORD = PackageRecord(name="pychoir", version="0.0.30", build="pypi_0", build_number=0)


@pytest.mark.parametrize(
    ("on_main_x", "main_x_configured", "authenticated"),
    [
        pytest.param(False, True, False, id="not-on-main-x-with-channel"),
        pytest.param(False, False, False, id="not-on-main-x-without-channel"),
        pytest.param(True, True, True, id="already-set-up"),
    ],
)
def test_handle_pnfe_returns_none(
    mocker: MockerFixture,
    on_main_x: bool,
    main_x_configured: bool,
    authenticated: bool,
) -> None:
    """No prompt when packages aren't on main-x, or the user is already set up."""
    mocker.patch("anaconda_channel_guide.plugin.is_available_on_main_x", return_value=on_main_x)

    result = handle_pnfe(
        ["pychoir"],
        main_x_configured=main_x_configured,
        authenticated=authenticated,
        subdirs=SUBDIRS,
    )
    assert result is None


def test_handle_pnfe_returns_none_when_no_packages() -> None:
    """No prompt when there are no missing packages to guide on."""
    result = handle_pnfe(
        [],
        main_x_configured=False,
        authenticated=False,
        subdirs=SUBDIRS,
    )
    assert result is None


@pytest.mark.parametrize(
    ("main_x_configured", "authenticated", "expected_steps"),
    [
        pytest.param(True, False, [LOGIN_CMD], id="needs-login-only"),
        pytest.param(False, True, [CONFIG_CMD], id="needs-config-only"),
        pytest.param(False, False, [LOGIN_CMD, CONFIG_CMD], id="needs-login-and-config"),
    ],
)
def test_handle_pnfe_prompts_required_steps(
    mocker: MockerFixture,
    main_x_configured: bool,
    authenticated: bool,
    expected_steps: list[str],
) -> None:
    """When packages are on main-x and setup is incomplete, prompt the missing steps."""
    mocker.patch("anaconda_channel_guide.plugin.is_available_on_main_x", return_value=True)

    result = handle_pnfe(
        ["pychoir"],
        main_x_configured=main_x_configured,
        authenticated=authenticated,
        subdirs=SUBDIRS,
    )
    assert isinstance(result, ChannelGuideBox)
    output = result.plain_text_message()
    for step in expected_steps:
        assert step in output


@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(True, id="valid-token"),
        pytest.param(False, id="expired-token"),
    ],
)
def test_is_logged_in(mocker: MockerFixture, expected: bool) -> None:
    """Verify is_logged_in reflects token state."""
    mock_cls = mocker.patch("anaconda_channel_guide.plugin.TokenInfo")
    mock_cls.load.return_value.expired = not expected
    assert is_logged_in() == expected


def test_is_logged_in_no_token(mocker: MockerFixture) -> None:
    """Verify user is not considered logged in if no token is found."""
    mock_cls = mocker.patch("anaconda_channel_guide.plugin.TokenInfo")
    mock_cls.load.side_effect = TokenNotFoundError("no token")
    assert not is_logged_in()


@pytest.mark.parametrize(
    ("channels", "expected"),
    [
        pytest.param((MAIN_X_CHANNEL_NAME,), True, id="main-x-only"),
        pytest.param(("defaults", MAIN_X_CHANNEL_NAME), True, id="main-x-with-defaults"),
        pytest.param((f"{MAIN_X_CHANNEL_NAME}/",), True, id="main-x-trailing-slash"),
        pytest.param(("defaults", "conda-forge"), False, id="no-main-x"),
        pytest.param((), False, id="empty-channels"),
        pytest.param(None, False, id="none-channels"),
    ],
)
def test_main_x_configured(
    channels: Iterable[str],
    expected: bool,
) -> None:
    assert is_main_x_configured(channels) is expected


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param("offline", id="offline"),
        pytest.param("json", id="json"),
    ],
)
def test_on_package_not_found_skips(
    mocker: MockerFixture,
    mode: str,
) -> None:
    """handle_pnfe is not called when conda is offline or in JSON mode."""
    mocker.patch("anaconda_channel_guide.hooks.context.plugins.anaconda_channel_guide", True)
    mocker.patch("anaconda_channel_guide.hooks.context.offline", mode == "offline")
    mocker.patch("anaconda_channel_guide.hooks.context.json", mode == "json")
    mock_handle = mocker.patch("anaconda_channel_guide.hooks.handle_pnfe")

    error = PackagesNotFoundInChannelsError(["pychoir"], channel_urls=("defaults",))
    hints = list(conda_error_hints(error))

    mock_handle.assert_not_called()
    assert hints == []


@pytest.fixture(scope="module")
def main_x_cache() -> None:
    """Load main-x repodata once so is_available_on_main_x can use the index cache."""
    from anaconda_channel_guide.prefetch import main

    main(list(context.subdirs))


@pytest.mark.usefixtures("main_x_cache")
@pytest.mark.parametrize(
    ("package", "expected"),
    [
        pytest.param("pychoir", True, id="found-on-main-x"),
        pytest.param("pychoir>0.0.29", True, id="found-on-main-x-version-satisfied"),
        pytest.param("pychoir<0.0.29", False, id="not-found-on-main-x"),
        pytest.param(MatchSpec("pychoir"), True, id="found-on-main-x-matchspec"),
        pytest.param(
            MatchSpec("pychoir>0.0.29"),
            True,
            id="found-on-main-x-version-satisfied-matchspec",
        ),
        pytest.param(MatchSpec("pychoir<0.0.29"), False, id="not-found-on-main-x-matchspec"),
    ],
)
def test_package_found_on_main_x(
    package: str | MatchSpec,
    expected: bool,
) -> None:
    """is_available_on_main_x uses real main-x repodata.
    Returns True when the spec matches at least one package on main-x,
    False when it does not (missing package or unsatisfied version).
    """
    assert is_available_on_main_x([package], subdirs=context.subdirs) is expected


def test_package_record_with_channel(mocker: MockerFixture) -> None:
    """A PackageRecord whose MatchSpec carries a channel is rejected."""
    mock_sd = mocker.patch("anaconda_channel_guide.plugin.SubdirData")
    mock_sd.query_all.return_value = (PYCHOIR_RECORD,)
    assert is_available_on_main_x([PYCHOIR_RECORD], subdirs=SUBDIRS) is False
    mock_sd.query_all.assert_not_called()


def test_query_raises_exception(mocker: MockerFixture) -> None:
    """A failed main-x query is treated as 'not available' rather than crashing."""
    mocker.patch("anaconda_channel_guide.plugin.SubdirData").query_all.side_effect = Exception()
    assert is_available_on_main_x(["pychoir"], subdirs=SUBDIRS) is False


@pytest.mark.parametrize(
    "package",
    [
        pytest.param("pychoir", id="str"),
        pytest.param(MatchSpec("pychoir"), id="matchspec"),
    ],
)
def test_query_receives_correct_args(mocker: MockerFixture, package: str | MatchSpec) -> None:
    """Subdirs and channels are forwarded to query_all."""
    mock_sd = mocker.patch("anaconda_channel_guide.plugin.SubdirData")
    mock_sd.query_all.return_value = (PYCHOIR_RECORD,)
    is_available_on_main_x([package], subdirs=SUBDIRS)
    mock_sd.query_all.assert_called_once_with(
        MatchSpec("pychoir"), channels=[MAIN_X_CHANNEL_URL], subdirs=SUBDIRS
    )


@pytest.mark.parametrize(
    "package",
    [
        pytest.param("conda-forge::numpy", id="str"),
        pytest.param(MatchSpec("conda-forge::numpy"), id="matchspec"),
    ],
)
def test_channel_pinned_spec(mocker: MockerFixture, package: str | MatchSpec) -> None:
    """Specs pinned to another channel, returns False."""
    mock_sd = mocker.patch("anaconda_channel_guide.plugin.SubdirData")

    assert is_available_on_main_x([package], subdirs=SUBDIRS) is False
    mock_sd.query_all.assert_not_called()


def test_availability_lookup_uses_index_cache(mocker: MockerFixture) -> None:
    """Use conda's cached repodata instead of refreshing on the PNFE path."""
    seen_use_index_cache = []

    def query_all(
        package: MatchSpec,
        *,
        channels: list[str],
        subdirs: tuple[str, ...],
    ) -> tuple[PackageRecord, ...]:
        assert package == MatchSpec("pychoir")
        assert channels == [MAIN_X_CHANNEL_URL]
        assert subdirs == SUBDIRS
        seen_use_index_cache.append(context.use_index_cache)
        return (PYCHOIR_RECORD,)

    mocker.patch("anaconda_channel_guide.plugin.SubdirData").query_all.side_effect = query_all

    with context._override("use_index_cache", False):
        assert is_available_on_main_x(["pychoir"], subdirs=SUBDIRS) is True
        assert seen_use_index_cache == [True]
        assert context.use_index_cache is False
