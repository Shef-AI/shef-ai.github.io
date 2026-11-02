#!/bin/bash
# Library presence / pkg-config checks for libabseil and libabseil-tests.
# Kept as a script (not a Jinja for-loop) so conda-lint can parse meta.yaml.

set -exuo pipefail

mode="${1:?usage: test-abseil-libs.sh <libabseil|libabseil-tests>}"
v_major="${PKG_VERSION%%.*}"

# shared builds for flags_* libraries are not supported on windows, see
# https://github.com/abseil/abseil-cpp/pull/1115
# (list kept here for parity with the Windows test script)
absl_libs_always_static_on_win=(
    decode_rust_punycode demangle_rust flags_commandlineflag flags_config flags_marshalling
    flags_parse flags_private_handle_accessor flags_program_name flags_reflection flags_usage
    hashtable_profiler log_flags poison profile_builder
)

absl_libs=(
    "${absl_libs_always_static_on_win[@]}"
    base civil_time crc_cord_state crc_cpu_detect crc32c cord cordz_functions
    cordz_handle cordz_info cordz_sample_token die_if_null examine_stack exponential_biased
    failure_signal_handler hash hashtablez_sampler int128 log_severity periodic_sampler
    random_distributions random_seed_gen_exception random_seed_sequences raw_hash_set
    scoped_set_env spinlock_wait stacktrace status statusor strerror strings
    symbolize synchronization throw_delegate time time_zone
)

# test helper targets (but used e.g. by protobuf)
absl_test_libs=(scoped_mock_log)

if [[ "${mode}" == "libabseil" ]]; then
    for each_lib in "${absl_libs[@]}"; do
        test -f "${PREFIX}/lib/libabsl_${each_lib}${SHLIB_EXT}"
        test ! -f "${PREFIX}/lib/libabsl_${each_lib}.a"
        pkg-config --print-errors --exact-version "${v_major}" "absl_${each_lib}"
    done

    for each_lib in "${absl_test_libs[@]}"; do
        test ! -f "${PREFIX}/lib/libabsl_${each_lib}${SHLIB_EXT}"
        test ! -f "${PREFIX}/lib/libabsl_${each_lib}.a"
    done
elif [[ "${mode}" == "libabseil-tests" ]]; then
    for each_lib in "${absl_test_libs[@]}"; do
        test -f "${PREFIX}/lib/libabsl_${each_lib}${SHLIB_EXT}"
        test ! -f "${PREFIX}/lib/libabsl_${each_lib}.a"
        pkg-config --print-errors --exact-version "${v_major}" "absl_${each_lib}"
    done
else
    echo "unknown mode: ${mode}" >&2
    exit 1
fi
