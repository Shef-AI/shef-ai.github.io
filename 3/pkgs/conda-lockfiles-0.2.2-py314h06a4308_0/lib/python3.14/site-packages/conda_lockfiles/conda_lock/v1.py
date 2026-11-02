from __future__ import annotations

import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal  # noqa: TCH003

from conda.base.context import context
from conda.common.serialize import yaml
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.plugins.types import EnvironmentSpecBase
from pydantic import BaseModel, Field, ValidationError
from ruamel.yaml import YAMLError
from ruamel.yaml.parser import ParserError

from .. import CONDA_PYPI_CHANNEL_NAME, PYTHONHOSTED_URL_PREFIX, __version__
from ..exceptions import CondaLockfilesParserError, CondaLockfilesValidationError
from ..load_yaml import load_yaml
from ..records_from_conda_urls import records_from_conda_urls
from ..validate_urls import validate_urls

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, Final

    from conda.common.path import PathType
    from conda.models.records import PackageRecord


#: The name of the conda-lock v1 format.
FORMAT: Final = "conda-lock-v1"

#: Aliases for the conda-lock v1 format. ``conda-lock`` is the unversioned
#: convenience alias and tracks the current stable ``conda-lock-v*``
#: format. See ``docs/format-aliases.md`` for the alias policy.
ALIASES: Final = ("conda-lock",)

#: The filename of the conda-lock v1 format.
CONDA_LOCK_FILE: Final = "conda-lock.yml"

#: Default filenames for the conda-lock v1 format.
DEFAULT_FILENAMES: Final = (CONDA_LOCK_FILE, "conda-lock.yaml")

#: The timestamp format for the conda-lock v1 format.
TIMESTAMP: Final = "%Y-%m-%dT%H:%M:%SZ"

#: Mapping of supported package types (as used in the lockfile) to package
#: managers (as used in the environment)
PACKAGE_TYPE_MAPPING: Final = {
    # "conda": "conda",  # processed as conda (explicit) packages
    "pip": "pypi",
}

PIP_EXPORT_WARNING: Final = (
    "This lockfile does not include the pip-installed packages "
    "in your environment.\n"
    "To fully reproduce this environment:\n"
    "  1. Identify the pip packages in your environment: conda list "
    "(look for 'pypi' channel)\n"
    "  2. Install the pip packages manually after applying the lockfile"
)


class CondaLockV1Hash(BaseModel):
    """Hash information for a package."""

    md5: str | None = None
    sha256: str | None = None


class CondaLockV1Package(BaseModel):
    """A package entry in the conda-lock v1 lockfile."""

    name: str
    version: str
    manager: Literal["conda", "pypi"]
    platform: str
    dependencies: Annotated[dict[str, str], Field(default_factory=dict)]
    url: str
    hash: Annotated[CondaLockV1Hash, Field(default_factory=CondaLockV1Hash)]
    category: str = "main"
    optional: bool = False


class CondaLockV1Channel(BaseModel):
    """A channel specification in the metadata."""

    url: str
    used_env_vars: Annotated[list[str], Field(default_factory=list)]


class CondaLockV1TimeMetadata(BaseModel):
    """Time metadata for the lockfile."""

    created_at: str


class CondaLockV1CustomMetadata(BaseModel):
    """Custom metadata for the lockfile."""

    created_by: str


class CondaLockV1Metadata(BaseModel):
    """Metadata section of the conda-lock v1 lockfile."""

    content_hash: Annotated[dict[str, str], Field(default_factory=dict)]
    channels: list[CondaLockV1Channel]
    platforms: Annotated[list[str], Field(min_length=1)]
    sources: Annotated[list[str], Field(default_factory=list)]
    time_metadata: CondaLockV1TimeMetadata | None = None
    custom_metadata: CondaLockV1CustomMetadata | None = None


class CondaLockV1(BaseModel):
    """The root structure of a conda-lock v1 file."""

    version: Annotated[int, Field(le=1, ge=1)] = 1
    metadata: CondaLockV1Metadata
    package: list[CondaLockV1Package]


def _record_to_package(
    record: PackageRecord,
    platform: str,
) -> CondaLockV1Package:
    """
    Convert a conda PackageRecord to a CondaLockV1Package Pydantic model.

    :param record: Conda package record
    :param platform: Platform string for this package
    :return: CondaLockV1Package with metadata
    """
    # Convert dependencies from list to dict
    dependencies = {}
    for dep in record.depends:
        ms = MatchSpec(dep)
        version = ms.version.spec_str if ms.version is not None else ""
        dependencies[ms.name] = version

    # Build hash dict
    hash_dict = CondaLockV1Hash(
        md5=record.md5,
        sha256=record.sha256,
    )

    return CondaLockV1Package(
        name=record.name,
        version=record.version,
        manager="conda",
        platform=platform,
        dependencies=dependencies,
        url=record.url,
        hash=hash_dict,
        category="main",
        optional=False,
    )


def conda_lock_v1_from_conda_envs(envs: Iterable[Environment]) -> CondaLockV1:
    """
    Create a CondaLockV1 lockfile from conda Environment objects.

    :param envs: Iterable of conda Environment objects
        (typically multiple platforms)
    :return: CondaLockV1 Pydantic model instance
    """
    # Convert to list to allow multiple iterations
    env_list = list(envs)

    # Check for pip packages and warn
    for env in env_list:
        if env.external_packages.get("pip"):
            warnings.warn(PIP_EXPORT_WARNING)
        validate_urls(env, FORMAT)

    # Generate timestamp
    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP)

    # Build packages list (no deduplication for v1 format)
    packages: list[CondaLockV1Package] = [
        _record_to_package(pkg, platform)
        for pkg, platform in sorted(
            # Canonical order is sorted by platform/subdir then by URL
            ((pkg, env.platform) for env in env_list for pkg in env.explicit_packages),
            key=lambda pkg_platform: (pkg_platform[1], pkg_platform[0].url),
        )
    ]

    # Build metadata from first environment
    # (all environments should have same channels for multiplatform export)
    env = env_list[0]
    channels = [
        CondaLockV1Channel(url=channel, used_env_vars=[])
        for channel in env.config.channels
    ]

    metadata = CondaLockV1Metadata(
        content_hash={},  # Empty for now, could be computed later
        channels=channels,
        platforms=sorted(e.platform for e in env_list),
        sources=[""],  # Empty source as before
        time_metadata=CondaLockV1TimeMetadata(created_at=timestamp),
        custom_metadata=CondaLockV1CustomMetadata(
            created_by=f"conda-lockfiles {__version__}"
        ),
    )

    # Construct and return CondaLockV1 instance
    return CondaLockV1(version=1, metadata=metadata, package=packages)


def conda_lock_v1_to_conda_env(
    lockfile: CondaLockV1,
    platform: str = context.subdir,
) -> Environment:
    """
    Render lockfile as a conda environment.

    :param lockfile: CondaLockV1 lockfile model
    :param platform: Platform to extract packages for
    :return: Conda Environment object
    """
    # Validate platform is available
    if platform not in lockfile.metadata.platforms:
        raise ValueError(
            f"Platform {platform} not found in lockfile. "
            f"Available platforms: {', '.join(lockfile.metadata.platforms)}"
        )

    config = EnvironmentConfig(
        channels=tuple(
            Channel(channel.url).canonical_name
            for channel in lockfile.metadata.channels
        ),
    )

    # Map conda-lock v1 packages to conda/external package records
    explicit_packages: dict[str, dict[str, Any]] = {}
    external_packages: dict[str, list[str]] = {}
    conda_pypi_channel = next(
        (
            channel.url
            for channel in lockfile.metadata.channels
            if Channel(channel.url).canonical_name == CONDA_PYPI_CHANNEL_NAME
        ),
        None,
    )
    for pkg in lockfile.package:
        # Filter packages
        if pkg.platform != platform:
            continue
        if pkg.category != "main":
            continue
        if pkg.optional:
            continue
        if not pkg.url:
            continue

        # Group by manager
        if pkg.manager == "conda":
            overrides = {
                "depends": [
                    f"{name} {version}" for name, version in pkg.dependencies.items()
                ],
                "name": pkg.name,
                "version": pkg.version,
                **pkg.hash.model_dump(exclude_none=True),
            }
            if conda_pypi_channel and pkg.url.startswith(PYTHONHOSTED_URL_PREFIX):
                overrides["channel"] = conda_pypi_channel
            explicit_packages[pkg.url] = overrides
        else:
            # Map conda-lock v1 package type to conda package type
            try:
                key = PACKAGE_TYPE_MAPPING[pkg.manager]
            except KeyError:
                raise ValueError(f"Unknown package type: {pkg.manager}")
            external_packages.setdefault(key, []).append(pkg.url)

    return Environment(
        prefix=context.target_prefix,
        platform=platform,
        config=config,
        explicit_packages=records_from_conda_urls(
            explicit_packages, dry_run=context.dry_run
        ),
        external_packages=external_packages,
    )


def multiplatform_export(envs: Iterable[Environment]) -> str:
    """Export Environment to conda-lock v1 format."""
    lockfile = conda_lock_v1_from_conda_envs(envs)
    try:
        # Exclude None values from serialization
        return yaml.dumps(lockfile.model_dump(exclude_none=True, mode="python"))
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to conda-lock v1 format: {e}"
        ) from e


class CondaLockV1Loader(EnvironmentSpecBase):
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()
        self._model: CondaLockV1 | None = None

    def can_handle(self) -> bool:
        """
        Attempts to validate loaded data as a conda lock v1 specification.

        :raises ValueError: Raised when validation fails
        """
        try:
            return self._validate_model()
        except (FileNotFoundError, YAMLError) as e:
            raise ValueError(f"Cannot load file {self.path}: {e}") from e

    def _validate_model(self) -> bool:
        """
        Attempt to load model.

        :returns: indicates successful load
        :raises ValueError: raised when validation fails
        """
        try:
            self._model = CondaLockV1.model_validate(self._data)
            return True
        except ValidationError as e:
            raise CondaLockfilesValidationError(e, self.path) from e

    @property
    def _data(self) -> dict[str, Any]:
        try:
            return load_yaml(self.path)
        except ParserError as e:
            raise CondaLockfilesParserError(e, self.path)

    @property
    def env(self) -> Environment:
        try:
            if self._model is None:
                self._validate_model()
            return conda_lock_v1_to_conda_env(self._model)
        except ValueError as e:
            raise CondaValueError(f"\n\nUnable to create environment: {e}") from e

    @property
    def available_platforms(self) -> tuple[str, ...]:
        """Platforms declared in this lockfile."""
        if self._model is None:
            self._validate_model()
        return tuple(self._model.metadata.platforms)

    def env_for(self, platform: str) -> Environment:
        """Return the Environment for a specific platform in the lockfile."""
        if platform not in self.available_platforms:
            raise ValueError(
                f"Platform {platform!r} not in lockfile. "
                f"Available platforms: {', '.join(self.available_platforms)}"
            )
        return conda_lock_v1_to_conda_env(self._model, platform=platform)
