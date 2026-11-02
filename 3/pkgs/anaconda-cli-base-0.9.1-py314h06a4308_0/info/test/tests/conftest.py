from __future__ import annotations

import os
import sys
from importlib import reload
from pathlib import Path
from types import ModuleType
from typing import IO
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Union
from typing import Generator

import pytest
import readchar
import typer
from typer import rich_utils
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from typer.testing import CliRunner
from click.testing import Result

# Force usage of new CLI
os.environ["ANACONDA_CLI_FORCE_NEW"] = "true"
os.environ["ANACONDA_CLI_DISABLE_PLUGINS"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import anaconda_cli_base.cli


class CLIInvoker(Protocol):
    def __call__(
        self,
        # app: typer.Typer,
        args: Optional[Union[str, Sequence[str]]] = None,
        input: Optional[Union[bytes, str, IO[Any]]] = None,
        env: Optional[Mapping[str, str]] = None,
        catch_exceptions: bool = True,
        color: bool = False,
        **extra: Any,
    ) -> Result: ...


@pytest.fixture(autouse=True)
def ensure_wide_terminal(monkeypatch: MonkeyPatch) -> None:
    """Ensure the terminal is wide enough for long output to stdout to prevent line breaks."""
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 10000)


@pytest.fixture
def disable_dot_env(mocker: MockerFixture) -> None:
    from anaconda_cli_base.config import AnacondaBaseSettings

    mocker.patch.dict(AnacondaBaseSettings.model_config, {"env_file": ""})


@pytest.fixture(autouse=True)
def disable_config_toml(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(tmp_path / "empty-config.toml"))


@pytest.fixture()
def tmp_cwd(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """Create & return a temporary directory after setting current working directory to it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def prepare_app() -> Generator[None, None, None]:
    reload(anaconda_cli_base.cli)

    @anaconda_cli_base.cli.app.command("some-test-subcommand")
    def some_test_subcommand() -> None:
        raise typer.Exit()

    yield


@pytest.fixture()
def invoke_cli(tmp_cwd: Path, monkeypatch: MonkeyPatch) -> CLIInvoker:
    """Returns a function, which can be used to call the CLI from within a temporary directory."""

    runner = CliRunner()

    # Construct a wrapper function so that we can also patch sys.argv when invoking the CLI
    def f(
        args: Optional[Union[str, Sequence[str]]] = None,
        input: Optional[Union[bytes, str, IO[Any]]] = None,
        env: Optional[Mapping[str, str]] = None,
        catch_exceptions: bool = True,
        color: bool = False,
        **extra: Any,
    ) -> Result:
        args = args or []
        monkeypatch.setattr(sys, "argv", ["path/to/anaconda"] + list(args))

        def mock_get_key(input_string: str) -> Callable[[], str]:
            """Generate a mock function for get_key, from an input string."""
            gen = (char for char in input_string)

            def get_key() -> str:
                try:
                    return next(gen)
                except StopIteration:
                    raise EOFError("No more input available")

            return get_key

        # We need to conditionally monkeypatch different modules, depending on the operating system
        module: ModuleType
        if sys.platform in ("win32", "cygwin"):
            module = readchar._win_read
        else:
            module = readchar._posix_read

        monkeypatch.setattr(module, "readchar", mock_get_key(str(input) or ""))

        return runner.invoke(
            anaconda_cli_base.cli.app,
            args=args,
            input=input,
            env=env,
            catch_exceptions=catch_exceptions,
            color=color,
            **extra,
        )

    return f
