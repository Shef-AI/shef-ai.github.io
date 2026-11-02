import importlib
import itertools
import os
import re
import subprocess
import sys
from importlib.metadata import Distribution
from functools import partial
from typing import Annotated
from typing import Tuple
from typing import Type
from typing import cast
from typing import Optional, Sequence, Callable, Generator, Union
from unittest.mock import MagicMock

import pytest
import typer
from packaging import version
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from readchar import key

import anaconda_cli_base.cli
from anaconda_cli_base import __version__
from anaconda_cli_base import console
from anaconda_cli_base.cli import _select_main_entrypoint_app
from anaconda_cli_base.exceptions import register_error_handler
from anaconda_cli_base.plugins import (
    load_registered_subcommands,
    _select_auth_handler_and_args,
)

from .conftest import CLIInvoker

ENTRY_POINT_TUPLE = Tuple[str, str, typer.Typer, Union[Distribution, None]]


installed_click_version = version.parse(importlib.metadata.version("click"))

# The click version where the exit code changed from 0 to 2 when no_args_is_help is used
click_version_exit_code_changed = version.parse("8.2.0")


def plugin_version_in_table(name: str, version: str, stdout: str) -> bool:
    matched = re.search(f"{re.escape(name)}\\s+│\\s+{re.escape(version)}", stdout)
    return matched is not None


@pytest.mark.parametrize(
    "args, expected_exit_code",
    [
        pytest.param(
            (),
            2 if installed_click_version >= click_version_exit_code_changed else 0,
            id="no-args",
        ),
        pytest.param(("--help",), 0, id="--help"),
        pytest.param(("-h",), 0, id="-h"),
    ],
)
@pytest.mark.parametrize(
    "expected_text",
    [
        "Welcome to the Anaconda CLI!",
        "Print debug information to the console.",
        "Show this message and exit.",
        "Show the version of this package and installed plugins and exit.",
    ],
)
def test_cli_help(
    invoke_cli: CLIInvoker,
    args: Tuple[str],
    expected_exit_code: int,
    expected_text: str,
) -> None:
    result = invoke_cli(args)
    assert result.exit_code == expected_exit_code
    assert expected_text in result.stdout


def test_cli_version(invoke_cli: CLIInvoker) -> None:
    result = invoke_cli(["--version"])
    assert result.exit_code == 0
    assert plugin_version_in_table("anaconda-cli-base", __version__, result.stdout)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param((), id="no-args"),
        pytest.param(("-t", "TOKEN"), id="-t"),
        pytest.param(("--token", "TOKEN"), id="--token"),
        pytest.param(("-s", "SITE"), id="-s"),
        pytest.param(("--site", "SITE"), id="--site"),
        pytest.param(("--disable-ssl-warnings",), id="--disable-ssl-warnings"),
        pytest.param(("--show-traceback",), id="--show-traceback"),
        pytest.param(("-v",), id="-v"),
        pytest.param(("--verbose",), id="--verbose"),
        pytest.param(("-q",), id="-q"),
        pytest.param(("--quiet",), id="--quiet"),
    ],
)
def test_cli_root_options_passthrough(invoke_cli: CLIInvoker, args: Tuple[str]) -> None:
    """Here, we make sure that the root options from anaconda-client are allowed to be passed in.

    These will get forwarded through to anaconda-client, but if not defined in typer app could
    raise unwanted exceptions.

    """
    result = invoke_cli([*args, "some-test-subcommand"])
    assert result.exit_code == 0


@pytest.fixture
def plugin(mocker: MockerFixture) -> ENTRY_POINT_TUPLE:
    plugin = typer.Typer(name="plugin", add_completion=False, no_args_is_help=True)

    @plugin.command("action")
    def action() -> None:
        print("done")

    dist = mocker.Mock(spec=Distribution)
    dist.name = "plugin"
    dist.version = "0.0.1plugin"
    return ("plugin", "plugin:app", plugin, dist)


def test_load_plugin(
    invoke_cli: CLIInvoker, plugin: ENTRY_POINT_TUPLE, mocker: MockerFixture
) -> None:
    plugins = [plugin]

    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    group = next(
        (
            group
            for group in anaconda_cli_base.cli.app.registered_groups
            if group.name == "plugin"
        ),
        None,
    )
    assert group is not None
    assert group.typer_instance == plugin[-2]

    result = invoke_cli(["plugin", "action"])
    assert result.exit_code == 0
    assert result.stdout == "done\n"

    result = invoke_cli(["--version"])
    assert result.exit_code == 0
    assert plugin_version_in_table("anaconda-cli-base", __version__, result.stdout)
    assert plugin_version_in_table("plugin", "0.0.1plugin", result.stdout)


@pytest.fixture
def dummy_plugin(monkeypatch: MonkeyPatch, mocker: MockerFixture) -> ENTRY_POINT_TUPLE:
    monkeypatch.setitem(
        anaconda_cli_base.plugins.AUTH_HANDLER_ALIASES, "dummy", "anaconda.com"
    )
    plugin = typer.Typer(name="dummy", add_completion=False, no_args_is_help=True)

    @plugin.command("action")
    def action() -> None:
        console.print("dummy: done")

    @plugin.command("login")
    def login(force: bool = typer.Option(False, "--force")) -> None:
        console.print("dummy: You're in")

    @plugin.command("logout")
    def logout() -> None:
        console.print("dummy: You're out")

    @plugin.command("whoami")
    def whoami() -> None:
        console.print("dummy: Who are you?")

    dist = mocker.Mock(spec=Distribution)
    dist.name = "auth-plugin"
    dist.version = "0.0.1auth-plugin"
    return ("dummy", "auth-plugin:app", plugin, dist)


def test_load_dummy_plugin(
    invoke_cli: CLIInvoker,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
) -> None:
    assert "login" not in [
        cmd.name for cmd in anaconda_cli_base.cli.app.registered_commands
    ]

    plugins = [dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    group = next(
        (
            group
            for group in anaconda_cli_base.cli.app.registered_groups
            if group.name == "dummy"
        ),
        None,
    )
    assert group is not None
    assert group.typer_instance == dummy_plugin[-2]

    for action in "login", "logout", "whoami":
        cmd = next(
            (
                cmd
                for cmd in anaconda_cli_base.cli.app.registered_commands
                if cmd.name == action
            ),
            None,
        )
        assert cmd is not None

    result = invoke_cli(["dummy", "action"])
    assert result.exit_code == 0
    assert result.stdout == "dummy: done\n"

    result = invoke_cli(["login"], input="\n")
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines()[-1].endswith("dummy: You're in")

    result = invoke_cli(["login", "--at", "dummy"])
    assert result.exit_code == 0
    assert result.stdout == "dummy: You're in\n"

    result = invoke_cli(["login", "--at", "anaconda.com"])
    assert result.exit_code == 0
    assert result.stdout == "dummy: You're in\n"

    result = invoke_cli(["login", "--at", "dummy", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout

    result = invoke_cli(["login", "--at", "anaconda.com", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout


@pytest.fixture
def org_plugin(mocker: MockerFixture) -> ENTRY_POINT_TUPLE:
    plugin = typer.Typer(name="org", add_completion=False, no_args_is_help=True)

    @plugin.command("action")
    def action() -> None:
        console.print("org: done")

    @plugin.command("token")
    def token(ctx: typer.Context) -> None:
        print(f"token: {ctx.obj.params.get('token')}")

    @plugin.command("login")
    def login(
        force: bool = typer.Option(False, "--force"),
        hostname: Optional[str] = typer.Option(None),
        username: Optional[str] = typer.Option(None),
        password: Optional[str] = typer.Option(None),
    ) -> None:
        console.print("org: You're in")

    @plugin.command("logout")
    def logout() -> None:
        console.print("org: You're out")

    @plugin.command("whoami")
    def whoami() -> None:
        console.print("org: Who are you?")

    dist = mocker.Mock(spec=Distribution)
    dist.name = "org-plugin"
    dist.version = "0.0.1a"
    return ("org", "org-plugin:app", plugin, dist)


@pytest.fixture
def legacy_main(mocker: MockerFixture) -> Generator[Callable, None, None]:
    def main(
        args: Optional[Sequence[str]] = None,
        *,
        exit_: bool = True,
        allow_plugin_main: bool = True,
    ) -> None:
        pass

    cli = MagicMock()
    cli.main = main
    modules = {
        "binstar_client": MagicMock(),
        "binstar_client.scripts": MagicMock(),
        "binstar_client.scripts.cli": cli,
    }
    mocker.patch.dict("sys.modules", modules)

    yield main


def test_org_legacy(
    org_plugin: ENTRY_POINT_TUPLE,
    legacy_main: Callable,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Mock the scenario where only anaconda-client was installed"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [org_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    assert [g.name for g in anaconda_cli_base.cli.app.registered_groups] == ["org"]

    final_app = _select_main_entrypoint_app(anaconda_cli_base.cli.app)

    assert isinstance(final_app, partial)
    assert final_app.func is legacy_main
    assert final_app.keywords["allow_plugin_main"] is False


def test_fail_org_legacy(
    org_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Mock the scenario where only anaconda-client was installed"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "True")
    monkeypatch.setenv("ANACONDA_CLIENT_FORCE_STANDALONE", "True")

    plugins = [org_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    with pytest.raises(ValueError):
        _ = _select_main_entrypoint_app(anaconda_cli_base.cli.app)


def test_force_org_legacy(
    org_plugin: ENTRY_POINT_TUPLE,
    legacy_main: Callable,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Multiple plugins installed but anaconda-client is the desired cli"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.setenv("ANACONDA_CLIENT_FORCE_STANDALONE", "True")

    plugins = [org_plugin, dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))
    groups = [g.name for g in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups
    assert "dummy" in groups

    final_app = _select_main_entrypoint_app(anaconda_cli_base.cli.app)

    assert isinstance(final_app, partial)
    assert final_app.func is legacy_main
    assert final_app.keywords["allow_plugin_main"] is False


def test_org_subcommand(
    invoke_cli: CLIInvoker,
    org_plugin: ENTRY_POINT_TUPLE,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Multiple plugins installed, default behavior"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [org_plugin, dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))
    groups = [g.name for g in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups
    assert "dummy" in groups

    final_app = _select_main_entrypoint_app(anaconda_cli_base.cli.app)

    assert final_app is anaconda_cli_base.cli.app

    for action in "login", "logout", "whoami":
        cmd = next(
            (
                cmd
                for cmd in anaconda_cli_base.cli.app.registered_commands
                if cmd.name == action
            ),
            None,
        )
        assert cmd is not None

    result = invoke_cli(["org", "action"])
    assert result.exit_code == 0
    assert "org: done\n" == result.stdout

    result = invoke_cli(["login", "--at", "org"])
    assert result.exit_code == 0
    assert result.stdout == "org: You're in\n"

    result = invoke_cli(["login", "--at", "anaconda.org"])
    assert result.exit_code == 0
    assert result.stdout == "org: You're in\n"


def test_org_login_explicit_username(
    invoke_cli: CLIInvoker,
    org_plugin: ENTRY_POINT_TUPLE,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Login with explicit --username and --password arguments doesn't raise an error."""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [org_plugin, dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))
    groups = [g.name for g in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups
    assert "dummy" in groups

    final_app = _select_main_entrypoint_app(anaconda_cli_base.cli.app)

    assert final_app is anaconda_cli_base.cli.app

    result = invoke_cli(
        [
            "login",
            "--at",
            "anaconda.org",
            "--username",
            "some-user",
            "--password",
            "secret-password",
        ]
    )
    assert result.exit_code == 0
    assert result.stdout == "org: You're in\n"


def test_login_select_multiple_plugins(
    invoke_cli: CLIInvoker,
    org_plugin: ENTRY_POINT_TUPLE,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Multiple plugins installed, default behavior"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [org_plugin, dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["login"])
    assert result.stdout.strip().startswith(
        "choose destination: \n * anaconda.com      \n   anaconda.org"
    )

    result = invoke_cli(["login"], input="\n")
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines()[-1].endswith("dummy: You're in")

    result = invoke_cli(["login"], input="j\n")
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines()[-1].endswith("org: You're in")

    result = invoke_cli(["login"], input="jk\n")
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines()[-1].endswith("dummy: You're in")

    result = invoke_cli(["login"], input=key.ENTER)
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip().splitlines()[-1].endswith("dummy: You're in")

    result = invoke_cli(["login"], input=key.DOWN + key.ENTER)
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip().splitlines()[-1].endswith("org: You're in")

    result = invoke_cli(["login"], input=key.DOWN + key.UP + key.ENTER)
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip().splitlines()[-1].endswith("dummy: You're in")


def test_login_select_hidden_org(
    invoke_cli: CLIInvoker,
    org_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Single plugin installed, selector hidden"""

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [org_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["login"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "org: You're in"


def test_login_select_hidden_cloud(
    invoke_cli: CLIInvoker,
    dummy_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
) -> None:
    """Single plugins installed, selector hidden"""

    plugins = [dummy_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["login"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "dummy: You're in"


def test_capture_top_level_params(
    invoke_cli: CLIInvoker,
    org_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    # Test that subcommand captures the top-level CLI params via the typer.Context.obj.params attribute.

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)
    monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "true")

    plugins = [org_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))
    groups = [g.name for g in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups

    final_app = _select_main_entrypoint_app(anaconda_cli_base.cli.app)

    assert final_app is anaconda_cli_base.cli.app

    result = invoke_cli(["--token", "TOKEN", "org", "token"])
    assert result.exit_code == 0
    assert "token: TOKEN\n" == result.stdout


@pytest.fixture
def error_plugin(mocker: MockerFixture) -> ENTRY_POINT_TUPLE:
    plugin = typer.Typer(name="error", add_completion=False, no_args_is_help=True)

    class MyException(Exception):
        pass

    @register_error_handler(MyException)
    def handle_exception(e: Type[Exception]) -> int:
        print(f"Custom error handler: {e.__class__.__name__}")
        return 42

    class AnotherException(Exception):
        pass

    @register_error_handler(AnotherException)
    def handle_and_continue(e: Type[Exception]) -> int:
        print(f"I've corrected the problem: {e.__class__.__name__}")
        return -1

    @plugin.command("auto-catch")
    def auth_catch(opt: Annotated[Optional[bool], typer.Option()] = None) -> None:
        _ = 1 / 0

    @plugin.command("custom-catch")
    def custom_catch(arg: Annotated[Optional[str], typer.Argument()] = None) -> None:
        raise MyException("something bad happened")

    class Counter:
        def __init__(self) -> None:
            self.count = 0

        def __call__(self) -> None:
            print("calling counter")
            self.count += 1
            if self.count < 2:
                raise AnotherException("Call me again")

    counter1 = Counter()
    counter2 = Counter()

    @plugin.command("continue-task")
    def continue_task() -> None:
        counter1()

    @plugin.command("continue-task-but-fail")
    def continue_task_but_fail() -> None:
        counter2()
        raise RuntimeError("something went wrong")

    dist = mocker.Mock(spec=Distribution)
    dist.name = "error-plugin"
    dist.version = "0.0.1a"
    return ("error", "error-plugin:app", plugin, dist)


def test_error_handled(
    invoke_cli: CLIInvoker,
    error_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    # Test that subcommand captures the top-level CLI params via the typer.Context.obj.params attribute.

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [error_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["error", "auto-catch"])
    assert result.exit_code == 1
    assert result.stdout.splitlines()[0] == "ZeroDivisionError: division by zero"

    result = invoke_cli(["--verbose", "error", "auto-catch"])
    assert result.exit_code == 1
    assert isinstance(result.exception, ZeroDivisionError)

    result = invoke_cli(["error", "custom-catch"])
    assert result.exit_code == 42
    assert result.stdout.splitlines()[0] == "Custom error handler: MyException"

    result = invoke_cli(["error", "continue-task"])
    assert result.exit_code == 0
    output = result.stdout.splitlines()
    assert output[:3] == [
        "calling counter",
        "I've corrected the problem: AnotherException",
        "calling counter",
    ]

    result = invoke_cli(["error", "continue-task-but-fail"])
    assert result.exit_code == 1
    output = result.stdout.splitlines()
    assert output[:4] == [
        "calling counter",
        "I've corrected the problem: AnotherException",
        "calling counter",
        "RuntimeError: something went wrong",
    ]


def test_error_handled_recommend_verbose(
    invoke_cli: CLIInvoker,
    error_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    # Test that subcommand captures the top-level CLI params via the typer.Context.obj.params attribute.

    # these env vars should not be set in a normal env for this test
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [error_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["error", "auto-catch"])
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[-1].strip() == "anaconda --verbose error auto-catch"

    result = invoke_cli(["error", "auto-catch", "--opt"])
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[-1].strip() == "anaconda --verbose error auto-catch --opt"

    result = invoke_cli(["error", "auto-catch", "--no-opt"])
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[-1].strip() == "anaconda --verbose error auto-catch --no-opt"

    result = invoke_cli(["error", "custom-catch"])
    assert result.exit_code == 42
    lines = result.stdout.splitlines()
    assert lines[-1].strip() == "anaconda --verbose error custom-catch"

    result = invoke_cli(["error", "custom-catch", "arg"])
    assert result.exit_code == 42
    lines = result.stdout.splitlines()
    assert lines[-1].strip() == "anaconda --verbose error custom-catch arg"


def test_error_handled_recommend_verbose_args_none(
    error_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the verbose hint includes args when main() is called with args=None.

    The real CLI entry point calls ErrorHandledGroup.main(args=None), which
    means Click reads sys.argv internally.  The error handler must still
    reconstruct the original command for the 'anaconda --verbose ...' hint.
    """
    monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)

    plugins = [error_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    app = cast(typer.Typer, anaconda_cli_base.cli.app)
    load_registered_subcommands(app)

    click_app = typer.main.get_command(app)

    # Simulate real CLI: args=None, sys.argv has the command
    monkeypatch.setattr(sys, "argv", ["anaconda", "error", "auto-catch"])
    with pytest.raises(SystemExit) as exc_info:
        click_app.main(args=None, standalone_mode=True)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "anaconda --verbose error auto-catch" in captured.out


@pytest.mark.parametrize(
    "options, top_options, expected_handler, expected_args",
    [
        pytest.param(
            {}, {"at": "anaconda.com"}, "dot-com-handler", [], id="dot-com-top-at"
        ),
        pytest.param(
            {}, {"at": "anaconda.org"}, "dot-org-handler", [], id="dot-org-top-at"
        ),
        pytest.param(
            {},
            {"at": "anaconda.org", "site": "foo"},
            "dot-org-handler",
            [],
            id="dot-org-top-at-site",
        ),
        pytest.param({}, {"site": "foo"}, "dot-org-handler", [], id="dot-org-top-site"),
        pytest.param(
            {}, {"token": "foo"}, "dot-org-handler", [], id="dot-org-top-token"
        ),
        pytest.param(
            {"at": "anaconda.com"}, {}, "dot-com-handler", [], id="dot-com-at"
        ),
        pytest.param(
            {"at": "anaconda.org"}, {}, "dot-org-handler", [], id="dot-org-at"
        ),
        pytest.param(
            {"username": "some-user"},
            {},
            "dot-org-handler",
            ["--username", "some-user"],
            id="dot-org-username",
        ),
        pytest.param(
            {"username": "some-user", "password": "secret-password"},
            {},
            "dot-org-handler",
            ["--username", "some-user", "--password", "secret-password"],
            id="dot-org-username-password",
        ),
        pytest.param(
            {"hostname": "some-hostname"},
            {},
            "dot-org-handler",
            ["--hostname", "some-hostname"],
            id="dot-org-hostname",
        ),
    ],
)
def test_select_auth_handler_and_args(
    options: dict[str, str],
    top_options: dict[str, str],
    expected_handler: str,
    expected_args: list[str],
    *,
    monkeypatch: MonkeyPatch,
) -> None:
    # Build a list like ["--at", "anaconda.org"] from the dictionary
    def make_options_list(options: dict[str, str]) -> list[str]:
        return list[str](
            itertools.chain.from_iterable(
                [f"--{option}", value] for option, value in options.items()
            )
        )

    options_list = make_options_list(options)
    top_options_list = make_options_list(top_options)
    # Patch the sys args
    monkeypatch.setattr(
        sys, "argv", ["/path/to/anaconda", *top_options_list, "login"] + options_list
    )

    # Construct a mapping of auth handlers, normally would be loaded via plugins
    dummy_auth_handlers = {
        "anaconda.com": "dot-com-handler",
        "anaconda.org": "dot-org-handler",
    }

    # Mock the context since we're not really calling the CLI
    ctx_mock = MagicMock()
    ctx_mock.args = []
    ctx_mock.obj.params = {}
    if "site" in top_options:
        ctx_mock.obj.params["site"] = top_options["site"]
    if "token" in top_options:
        ctx_mock.obj.params["token"] = top_options["token"]

    # Build the four possible options into a dictionary with defaults
    option_defaults = {
        "at": None,
        "username": None,
        "password": None,
        "hostname": None,
    }

    top_options_copy = top_options.copy()
    _ = top_options_copy.pop("site", None)
    _ = top_options_copy.pop("token", None)

    # Invoke the function
    handler, args = _select_auth_handler_and_args(
        ctx=ctx_mock,
        **{**option_defaults, **options, **top_options_copy},
        help=False,
        auth_handlers=dummy_auth_handlers,  # type: ignore
        auth_handlers_dropdown=[],
    )

    # Assert we select the right handler and parse into the correct arguments
    assert handler == expected_handler
    assert args == expected_args


def test_at_handler(
    invoke_cli: CLIInvoker,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANACONDA_DEFAULT_SITE", raising=False)

    result = invoke_cli(["--help"])
    assert "--at" in result.stdout
    assert "Select the configured site to use by name or domain" in result.stdout

    result = invoke_cli(["--at", "site-name", "--version"])
    assert os.getenv("ANACONDA_DEFAULT_SITE") == "site-name"


def test_python_m_invocation() -> None:
    """Ensure `python -m anaconda_cli_base` launches the CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "anaconda_cli_base", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "Welcome to the Anaconda CLI!" in result.stdout


def test_python_m_bad_command() -> None:
    """Ensure `python -m anaconda_cli_base` exits non-zero on unknown commands."""
    result = subprocess.run(
        [sys.executable, "-m", "anaconda_cli_base", "nonexistent-command"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
