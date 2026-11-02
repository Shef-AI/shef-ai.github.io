import os
from importlib.metadata import Distribution
from pathlib import Path
from textwrap import dedent
from typing import Optional, Tuple, cast, Dict, Iterator, Union

import pytest
import typer
from pydantic import Field
from pydantic import BaseModel
from pydantic import RootModel
from pydantic import ValidationError
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

import anaconda_cli_base.cli
from anaconda_cli_base.config import AnacondaBaseSettings
from anaconda_cli_base.config import AnacondaConfigTomlSettingsSource
from anaconda_cli_base.exceptions import AnacondaConfigTomlSyntaxError
from anaconda_cli_base.exceptions import AnacondaConfigValidationError
from anaconda_cli_base.plugins import load_registered_subcommands

from .conftest import CLIInvoker

ENTRY_POINT_TUPLE = Tuple[str, str, typer.Typer, Union[Distribution, None]]


class Nested(BaseModel):
    field: str = "default"


class DerivedSettings(AnacondaBaseSettings, plugin_name="derived"):
    foo: str = "default"
    nested: Nested = Nested()
    optional: Optional[int] = None
    not_required: Optional[str] = None
    docker_test: Optional[str] = "default"


def test_settings_plugin_name_str() -> None:
    env_prefix = DerivedSettings.model_config.get("env_prefix", "")
    assert env_prefix == "ANACONDA_DERIVED_"

    table_header = DerivedSettings.model_config.get(
        "pyproject_toml_table_header", tuple()
    )
    assert table_header == (
        "plugin",
        "derived",
    )


def test_settings_plugin_name_tuple() -> None:
    class TupleName(DerivedSettings, plugin_name=("nested", "settings")): ...

    env_prefix = TupleName.model_config.get("env_prefix", "")
    assert env_prefix == "ANACONDA_NESTED_SETTINGS_"

    table_header = TupleName.model_config.get("pyproject_toml_table_header", tuple())
    assert table_header == ("plugin", "nested", "settings")


def test_settings_plugin_name_error() -> None:
    with pytest.raises(ValueError):

        class FailList(DerivedSettings, plugin_name=["nested", "settings"]): ...

    with pytest.raises(ValueError):

        class FailType(DerivedSettings, plugin_name=["nested", 0]): ...


def test_settings_priority(
    mocker: MockerFixture, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))

    monkeypatch.setitem(DerivedSettings.model_config, "secrets_dir", tmp_path)
    secret_file = tmp_path / "anaconda_derived_docker_test"

    dotenv = tmp_path / ".env"
    mocker.patch.dict(DerivedSettings.model_config, {"env_file": dotenv})

    config = DerivedSettings()
    assert config.foo == "default"
    assert config.nested.field == "default"
    assert config.docker_test == "default"

    AnacondaConfigTomlSettingsSource._cache.clear()
    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = "toml"
        docker_test = "toml"
        [plugin.derived.nested]
        field = "toml"
    """)
    )
    config = DerivedSettings()
    assert config.foo == "toml"
    assert config.nested.field == "toml"
    assert config.docker_test == "toml"

    AnacondaConfigTomlSettingsSource._cache.clear()
    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = "toml"
        docker_test = "toml"
        nested = { field = "toml_inline" }
    """)
    )
    config = DerivedSettings()
    assert config.foo == "toml"
    assert config.nested.field == "toml_inline"
    assert config.docker_test == "toml"

    AnacondaConfigTomlSettingsSource._cache.clear()
    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = "toml"
        nested.field = "toml_dot"
        docker_test = "toml"
    """)
    )
    config = DerivedSettings()
    assert config.foo == "toml"
    assert config.nested.field == "toml_dot"
    assert config.docker_test == "toml"

    dotenv.write_text(
        dedent("""\
        ANACONDA_DERIVED_FOO=dotenv
        ANACONDA_DERIVED_NESTED__FIELD=dotenv
        ANACONDA_DERIVED_DOCKER_TEST=dotenv
    """)
    )
    config = DerivedSettings()
    assert config.foo == "dotenv"
    assert config.nested.field == "dotenv"
    assert config.docker_test == "dotenv"

    secret_file.write_text("secret")
    config = DerivedSettings()
    assert config.docker_test == "secret"

    monkeypatch.setenv("ANACONDA_DERIVED_FOO", "env")
    monkeypatch.setenv("ANACONDA_DERIVED_NESTED__FIELD", "env")
    monkeypatch.setenv("ANACONDA_DERIVED_DOCKER_TEST", "env")
    config = DerivedSettings()
    assert config.foo == "env"
    assert config.nested.field == "env"
    assert config.docker_test == "env"

    config = DerivedSettings(
        foo="init", nested=Nested(field="init"), docker_test="init"
    )
    assert config.foo == "init"
    assert config.nested.field == "init"
    assert config.docker_test == "init"


def test_subclass(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))

    class Subclass(DerivedSettings, plugin_name="subclass"): ...

    assert Subclass.model_config.get("env_prefix", "") == "ANACONDA_SUBCLASS_"

    config_file.write_text(
        dedent("""\
        [plugin.subclass]
        foo = "subclass-config"
    """)
    )

    config = Subclass()
    assert config.foo == "subclass-config"

    monkeypatch.setenv("ANACONDA_SUBCLASS_FOO", "subclass-env")
    config = Subclass()
    assert config.foo == "subclass-env"


def test_nested_plugins(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))

    class ExtrasConfig(AnacondaBaseSettings, plugin_name=("derived", "extras")):
        value: str = "default"

    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = "toml"
        [plugin.derived.nested]
        field = "toml"
        [plugin.derived.extras]
        value = "toml"
    """)
    )

    config = ExtrasConfig()
    assert config.value == "toml"

    monkeypatch.setenv("ANACONDA_DERIVED_EXTRAS_VALUE", "env")
    config = ExtrasConfig()
    assert config.value == "env"


def test_settings_toml_error(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))

    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = ["a"
        [plugin.derived.nested]
        field = "toml"
    """)
    )

    with pytest.raises(AnacondaConfigTomlSyntaxError) as excinfo:
        _ = DerivedSettings()

    assert (
        f"{os.sep}config.toml: Unclosed array (at line 3, column 1)"
        in excinfo.value.args[0]
    )


def test_settings_validation_error(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))
    monkeypatch.setenv("ANACONDA_DERIVED_OPTIONAL", "not-an-integer")

    config_file.write_text(
        dedent("""\
        [plugin.derived]
        foo = 1
        [plugin.derived.nested]
        field = [0, 1, 2]
    """)
    )

    with pytest.raises(AnacondaConfigValidationError) as excinfo:
        _ = DerivedSettings(not_required=3)  # type: ignore

    message = excinfo.value.args[0]
    assert f"{os.sep}config.toml in [plugin.derived] for foo = 1" in message
    assert (
        f"{os.sep}config.toml in [plugin.derived] for nested.field = [0, 1, 2]"
        in message
    )
    assert (
        "Error in environment variable ANACONDA_DERIVED_OPTIONAL=not-an-integer"
        in message
    )
    assert "Error in init kwarg DerivedSettings(not_required=3)" in message


@pytest.fixture
def config_error_plugin(
    tmp_path: Path, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> ENTRY_POINT_TUPLE:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))

    plugin = typer.Typer(name="error", add_completion=False, no_args_is_help=True)

    @plugin.command("syntax-error")
    def syntax_error() -> None:
        config_file.write_text(
            dedent("""\
            [plugin.derived]
            foo = ["a"
            [plugin.derived.nested]
            field = "toml"
        """)
        )
        _ = DerivedSettings()

    @plugin.command("validation-error")
    def validation_error() -> None:
        monkeypatch.setenv("ANACONDA_DERIVED_OPTIONAL", "not-an-integer")

        config_file.write_text(
            dedent("""\
            [plugin.derived]
            foo = 1
            [plugin.derived.nested]
            field = [0, 1, 2]
        """)
        )
        _ = DerivedSettings(not_required=3)  # type: ignore

    dist = mocker.Mock(spec=Distribution)
    dist.name = "config-error-plugin"
    dist.version = "0.0.1config-error"
    return ("config-error", "config-error-plugin:app", plugin, dist)


def test_error_handled(
    invoke_cli: CLIInvoker,
    config_error_plugin: ENTRY_POINT_TUPLE,
    mocker: MockerFixture,
) -> None:
    plugins = [config_error_plugin]
    mocker.patch(
        "anaconda_cli_base.plugins._load_entry_points_for_group", return_value=plugins
    )
    load_registered_subcommands(cast(typer.Typer, anaconda_cli_base.cli.app))

    result = invoke_cli(["config-error", "syntax-error"])
    assert result.exit_code == 1
    assert f"{os.sep}config.toml: Unclosed array (at line 3, column 1)" in result.stdout

    result = invoke_cli(["config-error", "validation-error"])
    assert result.exit_code == 1
    assert f"{os.sep}config.toml in [plugin.derived] for foo = 1" in result.stdout
    assert (
        f"{os.sep}config.toml in [plugin.derived] for nested.field = [0, 1, 2]"
        in result.stdout
    )
    assert (
        "Error in environment variable ANACONDA_DERIVED_OPTIONAL=not-an-integer"
        in result.stdout
    )
    assert "Error in init kwarg DerivedSettings(not_required=3)" in result.stdout


@pytest.fixture
def config_toml(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))
    yield config_file


def test_root_level_table(config_toml: Path) -> None:
    class RootLevelTable(AnacondaBaseSettings, plugin_name=None):
        foo: str = "bar"
        table: Optional[Dict[str, str]] = None

    config_toml.write_text(
        dedent("""\
            foo = "baz"
            [table]
            key = "value"
        """)
    )

    config = RootLevelTable()
    assert config.table == {"key": "value"}
    assert config.foo == "baz"


def test_table_name_reads_top_level_section(config_toml: Path) -> None:
    class TelemetryConfig(AnacondaBaseSettings, table_name="telemetry"):
        endpoint: Optional[str] = None
        anon_usage: bool = True

    config_toml.write_text(
        dedent("""\
            [telemetry]
            endpoint = "https://otel.anaconda.com:4317"
            anon_usage = false
        """)
    )

    config = TelemetryConfig()
    assert config.endpoint == "https://otel.anaconda.com:4317"
    assert config.anon_usage is False


def test_table_name_env_prefix(monkeypatch: MonkeyPatch, config_toml: Path) -> None:
    class TelemetryConfig(AnacondaBaseSettings, table_name="telemetry"):
        endpoint: Optional[str] = None

    monkeypatch.setenv("ANACONDA_TELEMETRY_ENDPOINT", "https://env-override.com:4317")

    config = TelemetryConfig()
    assert config.endpoint == "https://env-override.com:4317"


def test_table_name_write_config(config_toml: Path) -> None:
    class TelemetryConfig(AnacondaBaseSettings, table_name="telemetry"):
        endpoint: Optional[str] = None
        anon_usage: bool = True

    config = TelemetryConfig(endpoint="https://otel.anaconda.com:4317")
    config.write_config()

    contents = config_toml.read_text()
    assert "[telemetry]" in contents
    assert 'endpoint = "https://otel.anaconda.com:4317"' in contents
    assert "[plugin" not in contents


def test_table_name_and_plugin_name_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="Cannot specify both"):

        class BadConfig(AnacondaBaseSettings, plugin_name="foo", table_name="bar"):
            field: str = "value"


class NestedFlag(BaseModel):
    flag: bool = True


class Plugin(AnacondaBaseSettings, plugin_name="plugged"):
    foo: str = "bar"
    might_be_none: Optional[str] = "value"
    table: Optional[Dict[str, str]] = None
    nested: NestedFlag = NestedFlag()


def test_write_new_plugin_table_defaults_no_existing_file(config_toml: Path) -> None:
    plugged = Plugin()
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == "[plugin.plugged]\n"


def test_write_new_plugin_table_no_existing_file(config_toml: Path) -> None:
    plugged = Plugin(foo="foo")
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent("""\
        [plugin.plugged]
        foo = "foo"
    """)


def test_write_new_plugin_table_no_existing_file_without_null(
    config_toml: Path,
) -> None:
    plugged = Plugin(foo="foo", might_be_none=None)
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent("""\
        [plugin.plugged]
        foo = "foo"
    """)


def test_write_new_plugin_table_existing_file(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.other]
            key = "value"
            """
        )
    )

    plugged = Plugin(foo="foo")
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
            [plugin.other]
            key = "value"

            [plugin.plugged]
            foo = "foo"
            """
    )


def test_write_plugin_revert_to_default(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.plugged]
            foo = "foo"
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    plugged.foo = "bar"
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.plugged]
        foo = "bar"
        """
    )


def test_write_plugin_update_repopulates_cache(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.plugged]
            foo = "foo"
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    plugged.foo = "bar"
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.plugged]
        foo = "bar"
        """
    )

    reloaded = Plugin()
    assert reloaded.foo == "bar"


def test_write_plugin_revert_to_default_and_drop(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.plugged]
            foo = "foo"
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    plugged.foo = "bar"
    plugged.write_config(preserve_existing_keys=False)

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.plugged]
        """
    )


def test_write_nesting_update(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    plugged.table = {"key": "value"}

    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
    )


def test_write_nesting_update_revert_and_keep(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.nested]
            flag = false
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    assert plugged.nested == NestedFlag(flag=False)

    plugged.nested.flag = True

    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.nested]
            flag = true
            """
    )


def test_write_nesting_update_revert_and_drop(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.nested]
            flag = false
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"

    assert plugged.nested == NestedFlag(flag=False)

    plugged.nested.flag = True

    plugged.write_config(preserve_existing_keys=False)

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"
            """
    )


def test_write_remove_nesting_table(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
        )
    )

    plugged = Plugin()
    assert plugged.foo == "foo"
    assert plugged.table == {"key": "value"}

    plugged.table = None
    plugged.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"
            """
    )


def test_write_remove_plugin(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.plugged]
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
        )
    )

    plugin = Plugin(foo="bar", table=None)

    plugin.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.plugged]
        foo = "bar"
        """
    )


class RootConfig(AnacondaBaseSettings, plugin_name=None):
    foo: str = "bar"
    table: Optional[Dict[str, str]] = None


def test_write_root_level_key(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
        )
    )

    root = RootConfig(foo="root")

    root.write_config()

    contents = config_toml.read_text()

    assert contents == dedent(
        """\
            # a comment
            foo = "root"

            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
    )


def test_write_nested_update(config_toml: Path) -> None:
    class Nested(AnacondaBaseSettings, plugin_name="nested"):
        foo: str = "bar"
        table: Dict[str, str] = {}

    nested = Nested()
    nested.table["key"] = "value"

    nested.write_config()

    contents = config_toml.read_text()

    assert contents == dedent("""\
        [plugin.nested.table]
        key = "value"
        """)


def test_write_root_level_update(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            # a comment
            foo = "root"

            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"
            """
        )
    )

    root = RootConfig()
    assert root.foo == "root"

    root.table = {"key": "set-at-root"}
    root.write_config()

    contents = config_toml.read_text()

    assert contents == dedent(
        """\
            # a comment
            foo = "root"

            [plugin.plugged]
            # a comment
            foo = "foo"

            [plugin.plugged.table]
            key = "value"

            [table]
            key = "set-at-root"
            """
    )


def test_remove_root_level_table(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [table]
            key = "set-at-root"
            """
        )
    )

    root = RootConfig(table=None)
    root.write_config()

    contents = config_toml.read_text()
    assert contents == ""


class Item(BaseModel):
    key: Optional[str] = None
    key2: str = "default"


Mapping = RootModel[Dict[str, Item]]


class MappingPlugin(AnacondaBaseSettings, plugin_name="mapper"):
    map: Mapping = Mapping({})


def test_update_root_model_value_none_drop(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.mapper.map.foo]
            key = "foo"
            key2 = "non-default"

            [plugin.mapper.map.bar]
            key = "bar"
            """
        )
    )

    plugin = MappingPlugin()
    plugin.map.root["foo"].key = None
    plugin.map.root["foo"].key2 = "default"
    plugin.write_config(preserve_existing_keys=False)

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.mapper.map.foo]

        [plugin.mapper.map.bar]
        key = "bar"
        """
    )


def test_update_root_model_value_none_preserve(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.mapper.map.foo]
            key = "foo"
            key2 = "non-default"

            [plugin.mapper.map.bar]
            key = "bar"
            """
        )
    )

    plugin = MappingPlugin()
    plugin.map.root["foo"].key = None
    plugin.map.root["foo"].key2 = "default"
    plugin.write_config(preserve_existing_keys=True)

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.mapper.map.foo]
        key2 = "default"

        [plugin.mapper.map.bar]
        key = "bar"
        """
    )


def test_update_root_model_drop_key(config_toml: Path) -> None:
    config_toml.write_text(
        dedent(
            """\
            [plugin.mapper.map.foo]
            key = "foo"

            [plugin.mapper.map.bar]
            key = "bar"
            """
        )
    )

    plugin = MappingPlugin()
    del plugin.map.root["bar"]
    plugin.write_config()

    contents = config_toml.read_text()
    assert contents == dedent(
        """\
        [plugin.mapper.map.foo]
        key = "foo"
        """
    )


def test_write_validation_error(config_toml: Path) -> None:
    plugin = Plugin()

    with pytest.raises(ValidationError):
        plugin.foo = False  # type: ignore


class SubA(BaseModel):
    value: str = "default-a"


class SubB(BaseModel):
    value: str = "default-b"


class Container(BaseModel):
    a: SubA = Field(default_factory=SubA)
    b: SubB = Field(default_factory=SubB)


class MultiNestedPlugin(AnacondaBaseSettings, plugin_name="multi"):
    choice: str = "a"
    container: Container = Field(default_factory=Container)


@pytest.mark.parametrize("val", ["custom", "default-a"])
def test_write_sibling_nested_models_no_bleed(config_toml: Path, val: str) -> None:
    """Only the nested sub-model present in config should appear in output,
    even when its value matches the class default."""
    config_toml.write_text(
        dedent(f"""\
            [plugin.multi]
            choice = "a"
            [plugin.multi.container.a]
            value = "{val}"
        """)
    )

    plugin = MultiNestedPlugin()
    plugin.choice = "b"
    plugin.write_config()

    contents = config_toml.read_text()
    assert "[plugin.multi.container.a]" in contents
    assert "[plugin.multi.container.b]" not in contents
