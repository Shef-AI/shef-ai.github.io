# Copyright (C) 2019 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda plugin hooks for conda-content-trust.

This module registers:
- The `conda content-trust` subcommand for signing and verification tools
- The signature verification post-solve hook for verifying package signatures

Note: The signature verification hook was migrated from conda.trust in conda 26.3.
"""

import conda.plugins
import conda.plugins.types

from .cli import cli
from .verification import signature_verification


@conda.plugins.hookimpl
def conda_subcommands():
    """Register the content-trust subcommand."""
    yield conda.plugins.types.CondaSubcommand(
        name="content-trust",
        summary="Signing and verification tools for Conda",
        action=cli,
    )


@conda.plugins.hookimpl
def conda_post_solves():
    """Register the signature verification post-solve hook.

    This hook verifies package signatures during the solve phase,
    checking that package metadata is signed by trusted keys.

    The verification is only enabled when:
    - context.extra_safety_checks is True
    - context.signing_metadata_url_base is configured
    - Trust root and key manager metadata are available
    """
    yield conda.plugins.types.CondaPostSolve(
        name="signature-verification",
        action=signature_verification,
    )
