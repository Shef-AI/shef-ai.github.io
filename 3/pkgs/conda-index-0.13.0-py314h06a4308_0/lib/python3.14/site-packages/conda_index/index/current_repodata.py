"""
Build current_repodata.json, including newest packages and their dependencies,
and any other requested package versions.
"""

import copy
import json

# conda internals
from conda.base.context import context
from conda.core.subdir_data import SubdirData
from conda.exports import MatchSpec, Resolve, VersionOrder
from conda.models.channel import Channel

from ..utils import CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2


def _get_resolve_object(subdir, precs=None, repodata=None):
    packages = {}
    conda_packages = {}
    if not repodata:
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
            "packages.conda": conda_packages,
        }

    channel = Channel(f"https://conda.anaconda.org/dummy-channel/{subdir}")
    sd = SubdirData(channel)

    # repodata = copy.deepcopy(repodata) # slower than json.dumps/load loop
    repodata_copy = json.loads(json.dumps(repodata))

    # adds url, Channel objects to each repodata package
    sd._process_raw_repodata(repodata_copy)

    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in precs or sd._package_records}
    r = Resolve(index, channels=(channel,))
    return r


def _add_missing_deps(new_r, original_r):
    """For each package in new_r, if any deps are not satisfiable, backfill them from original_r."""

    expanded_groups = copy.deepcopy(new_r.groups)
    seen_specs = set()
    for g_name, g_recs in new_r.groups.items():
        for g_rec in g_recs:
            for dep_spec in g_rec.depends:
                if dep_spec in seen_specs:
                    continue
                ms = MatchSpec(dep_spec)
                if not new_r.find_matches(ms):
                    matches = original_r.find_matches(ms)
                    if matches:
                        version = matches[0].version
                        expanded_groups[ms.name] = set(
                            expanded_groups.get(ms.name, [])
                        ) | set(
                            original_r.find_matches(MatchSpec(f"{ms.name}={version}"))
                        )
                seen_specs.add(dep_spec)
    return [pkg for group in expanded_groups.values() for pkg in group]


def _add_prev_ver_for_features(new_r, orig_r):
    expanded_groups = copy.deepcopy(new_r.groups)
    for g_name in new_r.groups:
        if not any(m.track_features or m.features for m in new_r.groups[g_name]):
            # no features so skip
            continue

        # versions are sorted here so this is the latest
        latest_version = VersionOrder(str(new_r.groups[g_name][0].version))
        if g_name in orig_r.groups:
            # now we iterate through the list to find the next to latest
            # without a feature
            keep_m = None
            for i in range(len(orig_r.groups[g_name])):
                _m = orig_r.groups[g_name][i]
                if VersionOrder(str(_m.version)) <= latest_version and not (
                    _m.track_features or _m.features
                ):
                    keep_m = _m
                    break
            if keep_m is not None:
                expanded_groups[g_name] = {keep_m} | set(
                    expanded_groups.get(g_name, [])
                )

    return [pkg for group in expanded_groups.values() for pkg in group]


def _shard_newest_packages(subdir, r, pins=None):
    """Captures only the newest versions of software in the resolve object.

    For things where more than one version is supported simultaneously (like Python),
    pass pins as a dictionary, with the key being the package name, and the value being
    a list of supported versions.  For example:

    {'python': ["2.7", "3.6"]}
    """
    groups = {}
    pins = pins or {}
    for g_name, g_recs in r.groups.items():
        # always do the latest implicitly
        version = r.groups[g_name][0].version
        matches = set(r.find_matches(MatchSpec(f"{g_name}={version}")))
        if g_name in pins:
            for pin_value in pins[g_name]:
                version = r.find_matches(MatchSpec(f"{g_name}={pin_value}"))[0].version
                matches.update(r.find_matches(MatchSpec(f"{g_name}={version}")))
        groups[g_name] = matches

    # add the deps of the stuff in the index
    new_r = _get_resolve_object(
        subdir, precs=[pkg for group in groups.values() for pkg in group]
    )
    new_r = _get_resolve_object(subdir, precs=_add_missing_deps(new_r, r))

    # now for any pkg with features, add at least one previous version
    # also return
    return set(_add_prev_ver_for_features(new_r, r))


def build_current_repodata(subdir, repodata, pins):
    r = _get_resolve_object(subdir, repodata=repodata)
    keep_pkgs = _shard_newest_packages(subdir, r, pins)
    new_repodata = {
        k: repodata[k] for k in set(repodata.keys()) - {"packages", "packages.conda"}
    }
    packages = {}
    conda_packages = {}
    for keep_pkg in keep_pkgs:
        if keep_pkg.fn.endswith(CONDA_PACKAGE_EXTENSION_V2):
            conda_packages[keep_pkg.fn] = repodata["packages.conda"][keep_pkg.fn]
            # in order to prevent package churn we consider the md5 for the .tar.bz2 that matches the .conda file
            #    This holds when .conda files contain the same files as .tar.bz2, which is an assumption we'll make
            #    until it becomes more prevalent that people provide only .conda files and just skip .tar.bz2
            counterpart = keep_pkg.fn.replace(
                CONDA_PACKAGE_EXTENSION_V2, CONDA_PACKAGE_EXTENSION_V1
            )
            conda_packages[keep_pkg.fn]["legacy_bz2_md5"] = (
                repodata["packages"].get(counterpart, {}).get("md5")
            )
        elif keep_pkg.fn.endswith(CONDA_PACKAGE_EXTENSION_V1):
            packages[keep_pkg.fn] = repodata["packages"][keep_pkg.fn]
    new_repodata["packages"] = packages
    new_repodata["packages.conda"] = conda_packages
    return new_repodata
