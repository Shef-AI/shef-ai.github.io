from __future__ import annotations

import os
import shutil

import pytest

from anaconda_channel_guide.box import (
    CONFIG_STEP,
    DISABLE_STEP,
    LOGIN_STEP,
    MAX_WIDTH,
    TOS_MESSAGE,
    ChannelGuideBox,
)


def box_output(packages: list[str], steps: list[str]) -> str:
    """Get the output of a ChannelGuideBox for the given packages and steps"""
    return ChannelGuideBox(packages, steps).plain_text_message()


def test_always_present_content() -> None:
    """Ensure that content always appended by to_panel() is present in the output."""
    output = box_output(["package"], [])

    assert ChannelGuideBox.TITLE in output
    assert "Re-run the original command." in output
    assert all(line in output for line in DISABLE_STEP.splitlines() if line)
    assert all(line in output for line in TOS_MESSAGE.splitlines() if line)


@pytest.mark.parametrize(
    ("packages", "expected"),
    [
        pytest.param(
            ["pychoir"],
            "'pychoir' is available in Anaconda's 'main-x' channel.",
            id="single-package",
        ),
        pytest.param(
            ["pychoir", "aabbtree"],
            "'pychoir' and 'aabbtree' are available in Anaconda's 'main-x' channel.",
            id="two-packages",
        ),
        pytest.param(
            ["pychoir", "aabbtree", "numpy"],
            "'pychoir', 'aabbtree', and 'numpy' are available in Anaconda's 'main-x' channel.",
            id="three-packages",
        ),
    ],
)
def test_package_name_display(packages: list[str], expected: str) -> None:
    """Ensure that the package name(s) are displayed in the box with correct grammar."""
    assert expected in box_output(packages, [])


@pytest.mark.parametrize(
    ("steps", "expected_fragments"),
    [
        pytest.param(LOGIN_STEP, ["1. Log in:", "$ anaconda login"], id="login_only"),
        pytest.param(
            CONFIG_STEP,
            ["1. Add the 'main-x' channel:", "conda config --append default_channels"],
            id="config_only",
        ),
        pytest.param(
            [LOGIN_STEP, CONFIG_STEP],
            ["1. Log in:", "$ anaconda login", "2. Add the 'main-x' channel:"],
            id="login_and_config",
        ),
    ],
)
def test_expected_steps_in_box(steps: list[str] | str, expected_fragments: list[str]) -> None:
    """Ensure that the expected steps are displayed in the box."""
    step_list = [steps] if isinstance(steps, str) else steps
    output = box_output(["pychoir"], step_list)
    for fragment in expected_fragments:
        assert fragment in output


@pytest.mark.parametrize(
    ("packages", "expected_intro"),
    [
        pytest.param(
            ["numpy"],
            "'numpy' is available in Anaconda's 'main-x' channel.",
            id="single-package",
        ),
        pytest.param(
            ["numpy", "pandas"],
            "'numpy' and 'pandas' are available in Anaconda's 'main-x' channel.",
            id="two-packages",
        ),
        pytest.param(
            ["numpy", "pandas", "scipy"],
            "'numpy', 'pandas', and 'scipy' are available in Anaconda's 'main-x' channel.",
            id="three-packages",
        ),
    ],
)
def test_package_intro_formatting(packages: list[str], expected_intro: str) -> None:
    """Intro line uses correct grammar for one, two, or three packages."""
    box = ChannelGuideBox(packages, [])
    assert expected_intro in box.plain_text_message()


def test_steps_not_repeated_per_package() -> None:
    box = ChannelGuideBox(["a", "b"], [LOGIN_STEP, CONFIG_STEP])
    output = box.plain_text_message()
    assert output.count("$ anaconda login") == 1
    assert output.count("conda config --append default_channels") == 1


def _set_terminal_columns(monkeypatch: pytest.MonkeyPatch, columns: int) -> None:
    """Simulate `shutil.get_terminal_size()` reporting the given width."""
    monkeypatch.setattr(
        shutil,
        "get_terminal_size",
        lambda **_kwargs: os.terminal_size((columns, 24)),
    )


def _borders(output: str) -> tuple[str, str]:
    """Return the (top, bottom) border lines of a rendered box."""
    lines = [line for line in output.splitlines() if line]
    top = lines[0]
    bottom = next(line for line in lines if set(line) == {"-"})
    return top, bottom


@pytest.mark.parametrize(
    ("columns", "expected_top_width", "expected_bottom_width"),
    [
        pytest.param(0, MAX_WIDTH, MAX_WIDTH, id="zero-columns"),
        pytest.param(25, 50, 25, id="one-below-title-width"),
        pytest.param(26, 26, 26, id="exact-title-width"),
        pytest.param(84, 84, 84, id="at-max-width"),
        pytest.param(120, 84, 84, id="above-max-width"),
    ],
)
def test_border_width_for_columns(
    monkeypatch: pytest.MonkeyPatch,
    columns: int,
    expected_top_width: int,
    expected_bottom_width: int,
) -> None:
    """The top border must fit the title; the bottom border must fit the terminal."""
    _set_terminal_columns(monkeypatch, columns)
    top, bottom = _borders(box_output(["pychoir"], []))
    assert len(top) == expected_top_width
    assert len(bottom) == expected_bottom_width


@pytest.mark.parametrize(
    "columns",
    [
        pytest.param(0, id="zero-columns"),
        pytest.param(25, id="one-below-title-width"),
        pytest.param(26, id="exact-title-width"),
        pytest.param(84, id="at-max-width"),
        pytest.param(120, id="above-max-width"),
    ],
)
def test_title_has_dashes_on_both_sides(monkeypatch: pytest.MonkeyPatch, columns: int) -> None:
    """The title border must never be dropped or asymmetric, regardless of terminal size."""
    _set_terminal_columns(monkeypatch, columns)
    top, _bottom = _borders(box_output(["pychoir"], []))
    assert top.startswith("-")
    assert top.endswith("-")
    assert ChannelGuideBox.TITLE in top
