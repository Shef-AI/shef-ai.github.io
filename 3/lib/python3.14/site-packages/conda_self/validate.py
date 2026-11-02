from functools import cache
from importlib.metadata import entry_points

from conda.exceptions import CondaValueError


def _normalize(name: str) -> str:
    """Normalize package name for comparison (hyphens vs underscores)."""
    return name.lower().replace("_", "-")


@cache
def conda_plugin_packages():
    # Normalize names to use hyphens (conda convention) since
    # importlib.metadata may return underscores (Python convention).
    return set(
        _normalize(name)
        for ep in entry_points(group="conda")
        if ep.dist is not None
        and (name := ep.dist.name.strip())
        and _normalize(name) != "conda-self"
    )


def reload_plugin_packages() -> None:
    """Invalidate the cache to pick up newly installed packages."""
    conda_plugin_packages.cache_clear()


def validate_plugin_is_installed(name: str) -> None:
    if _normalize(name) not in conda_plugin_packages():
        raise CondaValueError(
            f"Package '{name}' does not seem to be a valid conda plugin. "
            "Try one of:\n- " + "\n- ".join(sorted(conda_plugin_packages()))
        )
