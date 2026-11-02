from __future__ import annotations

from typing import TYPE_CHECKING

from conda.common.io import dashlist

from .exceptions import EnvironmentExportNotSupported

if TYPE_CHECKING:
    from conda.models.environment import Environment


def validate_urls(env: Environment, format: str) -> None:
    missing_urls = [package for package in env.explicit_packages if package.url is None]
    if missing_urls:
        raise EnvironmentExportNotSupported(
            format,
            f"The following packages have no URL: {dashlist(missing_urls)}",
        )
