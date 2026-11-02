# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# type: ignore

from __future__ import annotations

import sys
from argparse import ArgumentParser, _StoreTrueAction
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

import pytest

from anaconda_cli_base.deprecations import DeprecatedError, DeprecationHandler

if TYPE_CHECKING:
    from packaging.version import Version

    DevDeprecationType = DeprecatedError
    UserDeprecationType = DeprecationWarning

PENDING = pytest.param(
    DeprecationHandler("1.0"),  # deprecated
    PendingDeprecationWarning,  # warning
    "pending deprecation",  # message
    id="pending",
)
FUTURE = pytest.param(
    DeprecationHandler("2.0"),  # deprecated
    FutureWarning,  # warning
    "deprecated",  # message
    id="future",
)
DEPRECATED = pytest.param(
    DeprecationHandler("2.0"),  # deprecated
    DeprecationWarning,  # warning
    "deprecated",  # message
    id="deprecated",
)
REMOVE = pytest.param(
    DeprecationHandler("3.0"),  # deprecated
    None,  # warning
    None,  # message
    id="remove",
)

parametrize_user = pytest.mark.parametrize(
    "deprecated,warning,message",
    [PENDING, FUTURE, REMOVE],
)
parametrize_dev = pytest.mark.parametrize(
    "deprecated,warning,message",
    [PENDING, DEPRECATED, REMOVE],
)


@parametrize_dev
def test_function(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated function displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated(deprecate_in="2.0", remove_in="3.0")
        def foo() -> bool:
            return True

        with pytest.warns(warning, match=message):  # type: ignore
            assert foo()


@parametrize_dev
def test_method(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated method displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        class Bar:
            @deprecated("2.0", "3.0")
            def foo(self) -> bool:
                return True

        with pytest.warns(warning, match=message):  # type: ignore
            assert Bar().foo()


@parametrize_dev
def test_class(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated class displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated("2.0", "3.0")
        class Foo:
            pass

        with pytest.warns(warning, match=message):  # type: ignore
            assert Foo()


@parametrize_dev
def test_arguments(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated argument displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated.argument("2.0", "3.0", "three")
        def foo(one: Any, two: Any) -> bool:
            return True

        # too many arguments, can only deprecate keyword arguments
        with pytest.raises(TypeError):
            assert foo(1, 2, 3)

        # alerting user to pending deprecation
        with pytest.warns(warning, match=message):  # type: ignore
            assert foo(1, 2, three=3)

        # normal usage not needing deprecation
        assert foo(1, 2)


@parametrize_user
def test_action(
    deprecated: DeprecationHandler,
    warning: UserDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated argparse.Action displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        parser = ArgumentParser()
        parser.add_argument(
            "--foo",
            action=deprecated.action("2.0", "3.0", _StoreTrueAction),
        )

        with pytest.warns(warning, match=message):  # type: ignore
            parser.parse_args(["--foo"])


@parametrize_dev
def test_module(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Importing a deprecated module displays associated warning (or error)."""
    context = (
        pytest.warns(warning, match=message)
        if warning
        else pytest.raises(DeprecatedError)
    )
    with context:
        deprecated.module("2.0", "3.0")


@parametrize_dev
def test_constant(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Using a deprecated constant displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        deprecated.constant("2.0", "3.0", "SOME_CONSTANT", 42)
        module = sys.modules[__name__]

        with pytest.warns(warning, match=message):  # type: ignore
            module.SOME_CONSTANT


@parametrize_dev
def test_topic(
    deprecated: DeprecationHandler,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Reaching a deprecated topic displays associated warning (or error)."""
    context = (
        pytest.warns(warning, match=message)
        if warning
        else pytest.raises(DeprecatedError)
    )
    with context:
        deprecated.topic("2.0", "3.0", topic="Some special topic")


def test_version_fallback() -> None:
    """Test that anaconda_client can run even if deprecations can't parse the version."""
    deprecated = DeprecationHandler(None)  # type: ignore[arg-type]
    assert deprecated._version_less_than("0")
    assert deprecated._version_tuple is None
    version: Version = deprecated._version_object  # type: ignore[assignment]
    assert version.major == version.minor == version.micro == 0
