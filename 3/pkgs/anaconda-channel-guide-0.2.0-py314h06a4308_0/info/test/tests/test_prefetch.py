import sys

from conda.base.context import context
from pytest_mock import MockerFixture

from anaconda_channel_guide.hooks import conda_pre_commands
from anaconda_channel_guide.plugin import MAIN_X_CHANNEL_NAME, MAIN_X_CHANNEL_URL
from anaconda_channel_guide.prefetch import (
    main,
    prefetch_main_x_repodata,
)


def test_pre_command_hook_registers_main_x_prefetch() -> None:
    hook = next(conda_pre_commands())

    assert hook.name == "channel-guide-main-x-prefetch"
    assert hook.action is prefetch_main_x_repodata
    assert hook.run_for == {"create", "env_create", "env_update", "install", "search"}


def test_prefetch_spawns_background_process(mocker: MockerFixture) -> None:
    popen = mocker.patch("anaconda_channel_guide.prefetch.subprocess.Popen")

    with (
        context._override("offline", False),
        context._override("channels", ()),
        context._override("_subdir", "osx-arm64"),
    ):
        prefetch_main_x_repodata("install")

    popen.assert_called_once()
    command = popen.call_args.args[0]
    assert command == [
        sys.executable,
        "-m",
        "anaconda_channel_guide.prefetch",
        "osx-arm64",
        "noarch",
    ]


def test_prefetch_skips_when_main_x_is_configured(mocker: MockerFixture) -> None:
    popen = mocker.patch("anaconda_channel_guide.prefetch.subprocess.Popen")
    mocker.patch.object(type(context), "channels", (f"{MAIN_X_CHANNEL_NAME}/",))

    with context._override("offline", False):
        prefetch_main_x_repodata("install")

    popen.assert_not_called()


def test_prefetch_child_loads_main_x_subdirs(mocker: MockerFixture) -> None:
    reset_context = mocker.patch("conda.base.context.reset_context")
    subdir_data = mocker.patch("conda.core.subdir_data.SubdirData")

    with (
        context._override("offline", False),
        context._override("subdir", "osx-arm64"),
    ):
        assert main(["osx-arm64", "noarch"]) == 0

    reset_context.assert_called_once_with()
    urls = [call.args[0].url() for call in subdir_data.call_args_list]
    assert urls == [
        f"{MAIN_X_CHANNEL_URL}/osx-arm64",
        f"{MAIN_X_CHANNEL_URL}/noarch",
    ]
    assert subdir_data.return_value.load.call_count == 2
