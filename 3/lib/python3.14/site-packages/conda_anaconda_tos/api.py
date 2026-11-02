# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level API functions for interacting with a channel's Terms of Service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from conda.auxlib.type_coercion import boolify
from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, get_local_metadatas, write_metadata
from .models import LocalPair, RemotePair
from .path import get_all_channel_paths, get_cache_paths
from .remote import get_remote_metadata

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Final


#: Boolean CI environment variables (checked with boolify)
#: Sources: Official CI platform documentation and community knowledge base
CI_BOOLEAN_VARS: Final = (
    "APPVEYOR",  # AppVeyor CI (https://www.appveyor.com/docs/environment-variables/)
    "BITRISE_IO",  # Bitrise (https://devcenter.bitrise.io/en/references/available-environment-variables.html)
    "BUDDY",  # Buddy CI/CD (https://buddy.works/docs/pipelines/environment-variables)
    "BUILDKITE",  # Buildkite (https://buildkite.com/docs/pipelines/environment-variables)
    "CI",  # Generic CI indicator (many platforms)
    "CIRCLECI",  # CircleCI (https://circleci.com/docs/variables/#built-in-environment-variables)
    "CIRRUS_CI",  # Cirrus CI (https://cirrus-ci.org/guide/environment-variables/)
    "CONCOURSE_CI",  # Concourse CI (https://concourse-ci.org/implementing-resource-types.html#environment)
    "DRONE",  # Drone CI (https://docs.drone.io/pipeline/environment/reference/)
    "GITHUB_ACTIONS",  # GitHub Actions (https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables)
    "GITLAB_CI",  # GitLab CI/CD (https://docs.gitlab.com/ee/ci/variables/predefined_variables.html)
    "SAIL_CI",  # Sail CI
    "SEMAPHORE",  # Semaphore CI (https://docs.semaphoreci.com/ci-cd-environment/environment-variables/)
    "TF_BUILD",  # Azure DevOps (Team Foundation) (https://docs.microsoft.com/en-us/azure/devops/pipelines/build/variables)
    "TRAVIS",  # Travis CI (https://docs.travis-ci.com/user/environment-variables/#default-environment-variables)
    "WERCKER",  # Wercker (deprecated)
    "WOODPECKER_CI",  # Woodpecker CI (https://woodpecker-ci.org/docs/usage/environment)
)

#: Presence-based CI environment variables (checked for existence)
#: Sources: Official CI platform documentation
CI_PRESENCE_VARS: Final = (
    "BAMBOO_BUILDKEY",  # Atlassian Bamboo (https://confluence.atlassian.com/bamboo/bamboo-variables-289277087.html)
    "CODEBUILD_BUILD_ID",  # AWS CodeBuild (https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-env-vars.html)
    "HEROKU_TEST_RUN_ID",  # Heroku CI (https://devcenter.heroku.com/articles/heroku-ci#environment-variables)
    "JENKINS_URL",  # Jenkins (https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables)
    "TEAMCITY_VERSION",  # JetBrains TeamCity (https://www.jetbrains.com/help/teamcity/predefined-build-parameters.html)
)


#: Container indicators for cgroup detection
#: Reference: https://github.com/containers/podman/issues/3586,
#: Docker/containerd documentation
CONTAINER_INDICATORS: Final = (
    "containerd",  # containerd runtime
    "docker",  # Docker containers
    "kubepods",  # Kubernetes pods (https://kubernetes.io/docs/tasks/administer-cluster/migrating-from-dockershim/find-out-runtime-you-use/)
    "lxc",  # Linux Containers
    "podman",  # Podman containers
)

#: Partial CI environment variables (used with container detection)
#: These variables may be present in containerized CI environments that don't
#: set full CI variables
PARTIAL_CI_VARS: Final = (
    "AZURE_HTTP_USER_AGENT",  # Azure DevOps user agent
    "BUILD_ID",  # Generic build identifier (Jenkins, etc.)
    "BUILD_NUMBER",  # Generic build number (Jenkins, etc.)
    "BUILD_URL",  # Generic build URL (Jenkins, etc.)
    "BUILDKITE_BUILD_ID",  # Buildkite build identifier
    "CIRCLE_BUILD_NUM",  # CircleCI build number
    "CIRCLE_PROJECT_REPONAME",  # CircleCI repository name
    "GITHUB_JOB",  # GitHub Actions job name
    "GITHUB_REPOSITORY",  # GitHub repository name
    "GITHUB_WORKFLOW",  # GitHub Actions workflow name
    "GITLAB_PROJECT_ID",  # GitLab project identifier
    "GITLAB_USER_ID",  # GitLab user identifier
    "JOB_NAME",  # Generic job name (Jenkins, etc.)
    "RUNNER_ARCH",  # GitHub Actions runner architecture
    "RUNNER_OS",  # GitHub Actions runner OS
    "WORKSPACE",  # Generic workspace path (Jenkins, etc.)
)


def _in_ci_container() -> bool:
    """Detect if running in a containerized CI environment.

    This function combines container detection with partial CI environment variables
    to address cases where CI systems run jobs in containers but don't set complete
    CI environment variables (see GitHub issue #232). This is a workaround for
    https://github.com/anaconda/conda-anaconda-tos/issues/232.

    Returns:
        bool: True if both container indicators and partial CI variables are present

    """
    # Check documented container indicators
    container_checks = [
        os.getpid() == 1,  # Process ID 1 (init process in containers)
        bool(os.environ.get("CONTAINER")),  # Generic container environment variable
    ]

    # Check cgroup for container runtime identifiers (Docker official method)
    # Reference: https://docs.docker.com/engine/containers/runmetrics/#find-the-cgroup-for-a-given-container
    try:
        with Path("/proc/self/cgroup").open() as f:
            cgroup_content = f.read()
            # Container runtime signatures in cgroups (documented by Docker):
            # - "docker": Docker containers
            # - "containerd": containerd runtime
            # - "kubepods": Kubernetes pods
            # - "lxc": Linux Containers
            # - "podman": Podman containers
            if any(indicator in cgroup_content for indicator in CONTAINER_INDICATORS):
                container_checks.append(True)
    except OSError:
        # Ignore errors (e.g., on non-Linux systems or restricted access)
        pass

    # Return True only if we detect container AND partial CI indicators
    # This prevents false positives from containers without CI context
    return any(container_checks) and any(os.getenv(var) for var in PARTIAL_CI_VARS)


def _is_ci() -> bool:
    """Determine if running in a CI environment.

    This function uses a multi-layered approach to detect CI environments:
    1. First checks if any CI variables are explicitly set to false
       (respects user override)
    2. Then checks boolean CI variables for true values
    3. Finally checks presence-based variables and container environments

    Returns:
        bool: True if running in a detected CI environment

    """
    # Check all boolean CI variables for explicit false values first
    # If any CI variable is explicitly set to false, respect that
    for var_value in map(os.getenv, CI_BOOLEAN_VARS):
        if var_value and not boolify(var_value):
            return False

    # Check boolean CI environment variables for true values
    for var_value in map(os.getenv, CI_BOOLEAN_VARS):
        if boolify(var_value):
            return True

    # Check presence-based CI environment variables
    return any(os.getenv(var) for var in CI_PRESENCE_VARS) or _in_ci_container()


#: Whether the current environment is a CI environment
CI: Final = _is_ci()

#: Whether the current environment is a Jupyter environment
JUPYTER: Final = os.getenv("JPY_SESSION_NAME") and os.getenv("JPY_PARENT_PID")


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    """Yield all unique channels from the given channels."""
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            channel = Channel(channel.base_url)
            if channel not in seen:
                yield channel
                seen.add(channel)


def get_one_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair | RemotePair:
    """Get the Terms of Service metadata for the given channel."""
    # fetch remote metadata
    remote_metadata = remote_exc = None
    try:
        remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)
    except CondaToSMissingError as exc:
        # CondaToSMissingError: no remote metadata
        remote_exc = exc

    # fetch local metadata
    try:
        local_pair = get_local_metadata(channel, extend_search_path=[tos_root])
    except CondaToSMissingError as exc:
        # CondaToSMissingError: no local metadata
        if remote_exc:
            raise remote_exc from exc
        # no local ToS metadata
        return RemotePair(metadata=remote_metadata)
    else:
        # return local metadata, include remote metadata if newer
        if not remote_metadata or local_pair.metadata >= remote_metadata:
            return local_pair
        return LocalPair(
            metadata=local_pair.metadata,
            path=local_pair.path,
            remote=remote_metadata,
        )


def get_stored_tos(
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, LocalPair]]:
    """Yield metadata of all stored Terms of Service."""
    for channel, local_pair in get_local_metadatas(extend_search_path=[tos_root]):
        try:
            remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            # CondaToSMissingError: no remote metadata
            continue

        # yield local metadata, include remote metadata if newer
        if local_pair.metadata >= remote_metadata:
            yield channel, local_pair
        else:
            yield (
                channel,
                LocalPair(
                    metadata=local_pair.metadata,
                    path=local_pair.path,
                    remote=remote_metadata,
                ),
            )


def accept_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair:
    """Accept the Terms of Service for the given channel."""
    pair = get_one_tos(
        channel,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )
    metadata = pair.remote or pair.metadata
    return write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair:
    """Reject the Terms of Service for the given channel."""
    pair = get_one_tos(
        channel,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )
    metadata = pair.remote or pair.metadata
    return write_metadata(tos_root, channel, metadata, tos_accepted=False)


def get_all_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, LocalPair | RemotePair | None]]:
    """List all channels and whether their Terms of Service have been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield (
                channel,
                get_one_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout),
            )
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other channels whose Terms of Service have been accepted/rejected
    for channel, metadata_pair in get_stored_tos(
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)


def clean_cache() -> Iterator[Path]:
    """Clean all metadata cache files."""
    for path in get_cache_paths():
        try:
            path.unlink()
        except (PermissionError, FileNotFoundError, IsADirectoryError):
            # PermissionError: no permission to delete the file
            # FileNotFoundError: the file doesn't exist
            # IsADirectoryError: the path is a directory
            pass
        else:
            yield path


def clean_tos(tos_root: str | os.PathLike[str] | Path) -> Iterator[Path]:
    """Clean all metadata directories."""
    for path in get_all_channel_paths(extend_search_path=[tos_root]):
        try:
            path.unlink()
        except (PermissionError, FileNotFoundError, IsADirectoryError):
            # PermissionError: no permission to delete the file
            # FileNotFoundError: the file doesn't exist
            # IsADirectoryError: the path is a directory
            pass
        else:
            yield path
