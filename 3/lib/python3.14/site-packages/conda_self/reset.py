from __future__ import annotations

import re
import sys
from os.path import dirname, isfile
from typing import TYPE_CHECKING

from conda import CondaError, CondaExitZero, CondaMultiError
from conda.base.constants import EXPLICIT_MARKER
from conda.base.context import context
from conda.common.io import dashlist
from conda.common.path import get_major_minor_version
from conda.core.link import PrefixSetup, UnlinkLinkTransaction
from conda.core.package_cache_data import PackageCacheData
from conda.core.prefix_data import PrefixData
from conda.core.solve import diff_for_unlink_link_precs
from conda.exceptions import ChecksumMismatchError, CondaSignalInterrupt, ParseError
from conda.gateways.disk.read import compute_sum, yield_lines
from conda.misc import _match_specs_from_explicit, get_package_records_from_explicit
from conda.models.enums import NoarchType
from conda.models.match_spec import MatchSpec
from conda_package_handling.exceptions import InvalidArchiveError

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.records import PackageRecord


def records_from_snapshot(
    prefix: str, snapshot_content: list[str]
) -> tuple[tuple[PackageRecord, ...], tuple[MatchSpec, ...]]:
    """Return package records for the snapshot and MatchSpecs to install or relink."""
    entries = tuple(line for line in snapshot_content if line != EXPLICIT_MARKER)
    try:
        specs = tuple(_match_specs_from_explicit(entries))
    except (ParseError, ValueError, IndexError, re.error):
        raise ParseError("Could not parse a package URL in the snapshot.") from None
    prefix_data = PrefixData(prefix)
    installed_python = prefix_data.get("python", None)
    snapshot_python = next((spec for spec in specs if spec.name == "python"), None)
    snapshot_python_version = (
        snapshot_python.get_exact_value("version")
        if snapshot_python is not None
        else None
    )
    relink_noarch_python = bool(
        installed_python is not None
        and snapshot_python_version
        and get_major_minor_version(installed_python.version)
        != get_major_minor_version(snapshot_python_version)
    )

    records: list[PackageRecord | None] = [None] * len(entries)
    unresolved_entries: list[str] = []
    unresolved_specs: list[MatchSpec] = []
    unresolved_indices: list[int] = []

    for index, (entry, spec) in enumerate(zip(entries, specs, strict=True)):
        installed_record = next(iter(prefix_data.query(spec)), None)
        needs_python_relink = bool(
            installed_record is not None
            and relink_noarch_python
            and installed_record.noarch == NoarchType.python
        )
        if installed_record is not None and not needs_python_relink:
            records[index] = installed_record
            continue

        unresolved_entries.append(entry)
        unresolved_specs.append(spec)
        unresolved_indices.append(index)

    if unresolved_entries:
        try:
            fetched_records = tuple(
                get_package_records_from_explicit(unresolved_entries)
            )
            checksum_errors = []
            for spec, record in zip(unresolved_specs, fetched_records, strict=True):
                url = spec.get_exact_value("url")
                if not url or not url.startswith("file:"):
                    continue
                archive = record.package_tarball_full_path
                if not isfile(archive):
                    continue
                # Conda trusts the requested checksum when copying a local package.
                for checksum_type in ("md5", "sha256"):
                    expected_checksum = spec.get_exact_value(checksum_type)
                    if expected_checksum is None:
                        continue
                    actual_checksum = compute_sum(archive, checksum_type)
                    if actual_checksum != expected_checksum:
                        # Keep the extracted cache usable only for its actual bytes.
                        setattr(record, checksum_type, actual_checksum)
                        PackageCacheData(dirname(archive)).insert(record)
                        checksum_errors.append(
                            ChecksumMismatchError(
                                url,
                                archive,
                                checksum_type,
                                expected_checksum,
                                actual_checksum,
                            )
                        )
            if checksum_errors:
                raise CondaMultiError(checksum_errors)
        except (CondaError, InvalidArchiveError) as error:
            pending_errors = [error]
            found_error = False
            while pending_errors:
                nested_error = pending_errors.pop()
                if isinstance(nested_error, CondaMultiError):
                    pending_errors.extend(nested_error.errors)
                elif type(nested_error) is RuntimeError and str(
                    nested_error
                ).startswith(
                    f"{InvalidArchiveError.__module__}."
                    f"{InvalidArchiveError.__qualname__}: "
                ):
                    # Conda 26.7 extraction workers wrap unpicklable errors in
                    # RuntimeError, retaining only the qualified type and message.
                    found_error = True
                elif not isinstance(
                    nested_error, (CondaError, InvalidArchiveError)
                ) or isinstance(nested_error, (CondaExitZero, CondaSignalInterrupt)):
                    raise
                else:
                    found_error = True
            if not found_error:
                raise

            packages = dashlist(
                spec.get_exact_value("fn") or spec.name for spec in unresolved_specs
            )
            raise CondaError(
                "Could not make all conda packages required by the selected "
                "snapshot available in a package cache.\n"
                "Required conda packages:%(packages)s\n"
                "The target environment was not changed. Some conda packages "
                "may have been downloaded and extracted into a package cache. "
                "Ensure each listed package is available in a package cache or "
                "can be downloaded from the URL in the snapshot, verified using "
                "its recorded checksum when present, and extracted, then retry.",
                packages=packages,
            ) from None

        for index, record in zip(unresolved_indices, fetched_records, strict=True):
            records[index] = record

    return tuple(
        dict.fromkeys(record for record in records if record is not None)
    ), tuple(unresolved_specs)


def names_from_explicit(path: Path) -> set[str]:
    """Extract package names from a CEP 23 explicit spec file without downloading.

    Parses each URL line with :class:`~conda.models.match_spec.MatchSpec`,
    which reads ``name``/``version``/``build`` from the package filename and
    strips any checksum fragment as a comment. No network access, unlike
    :func:`conda.misc.get_package_records_from_explicit`.
    """
    return {
        MatchSpec(line).name for line in yield_lines(path) if line != EXPLICIT_MARKER
    }


def reset(
    prefix: str = sys.prefix,
    uninstallable_packages: set[str] = set(),
    snapshot: Path | None = None,
):
    if snapshot:
        snapshot_content = list(yield_lines(snapshot))
        packages_in_reset_env, unresolved_specs = records_from_snapshot(
            prefix, snapshot_content
        )
        packages_to_remove, packages_to_install = diff_for_unlink_link_precs(
            prefix,
            packages_in_reset_env,
            specs_to_add=unresolved_specs,
            force_reinstall=True,
        )
        if not packages_to_remove and not packages_to_install:
            if not context.json and not context.quiet:
                print(
                    "Nothing to do. "
                    "The conda packages in the target environment match the "
                    "selected snapshot."
                )
            return
    else:
        installed = sorted(PrefixData(prefix).iter_records(), key=lambda x: x.name)
        packages_to_remove = tuple(
            pkg for pkg in installed if pkg.name not in uninstallable_packages
        )
        packages_to_install = ()

    stp = PrefixSetup(
        target_prefix=prefix,
        unlink_precs=packages_to_remove,
        link_precs=packages_to_install,
        remove_specs=(),
        update_specs=(),
        neutered_specs=(),
    )

    txn = UnlinkLinkTransaction(stp)
    if not context.json and not context.quiet:
        txn.print_transaction_summary()
    txn.execute()
