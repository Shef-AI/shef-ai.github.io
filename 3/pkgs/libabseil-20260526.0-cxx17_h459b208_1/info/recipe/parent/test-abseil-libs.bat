@echo on
REM Library presence / pkg-config checks for libabseil and libabseil-tests.
REM Kept as a script (not a Jinja for-loop) so conda-lint can parse meta.yaml.

SetLocal EnableDelayedExpansion

if "%~1"=="" (
    echo usage: test-abseil-libs.bat ^<libabseil^|libabseil-tests^>
    exit /b 1
)
set "MODE=%~1"

for /f "tokens=1 delims=." %%a in ("%PKG_VERSION%") do set "V_MAJOR=%%a"

REM shared builds for flags_* libraries are not supported on windows, see
REM https://github.com/abseil/abseil-cpp/pull/1115
set "ALWAYS_STATIC=decode_rust_punycode demangle_rust flags_commandlineflag flags_config flags_marshalling flags_parse flags_private_handle_accessor flags_program_name flags_reflection flags_usage hashtable_profiler log_flags poison profile_builder"

set "ABSL_LIBS=%ALWAYS_STATIC% base civil_time crc_cord_state crc_cpu_detect crc32c cord cordz_functions cordz_handle cordz_info cordz_sample_token die_if_null examine_stack exponential_biased failure_signal_handler hash hashtablez_sampler int128 log_severity periodic_sampler random_distributions random_seed_gen_exception random_seed_sequences raw_hash_set scoped_set_env spinlock_wait stacktrace status statusor strerror strings symbolize synchronization throw_delegate time time_zone"

set "ABSL_TEST_LIBS=scoped_mock_log"

if "%MODE%"=="libabseil" (
    for %%L in (%ABSL_LIBS%) do (
        set "IS_STATIC=0"
        for %%S in (%ALWAYS_STATIC%) do (
            if /I "%%L"=="%%S" set "IS_STATIC=1"
        )
        if "!IS_STATIC!"=="1" (
            if not exist "%LIBRARY_LIB%\absl_%%L.lib" exit 1
        ) else (
            if exist "%LIBRARY_LIB%\absl_%%L.lib" exit 1
        )
        pkg-config --print-errors --exact-version "!V_MAJOR!" absl_%%L
        if errorlevel 1 exit 1
    )

    for %%L in (%ABSL_TEST_LIBS%) do (
        if exist "%LIBRARY_LIB%\absl_%%L.lib" exit 1
    )
) else if "%MODE%"=="libabseil-tests" (
    for %%L in (%ABSL_TEST_LIBS%) do (
        pkg-config --print-errors --exact-version "!V_MAJOR!" absl_%%L
        if errorlevel 1 exit 1
    )
) else (
    echo unknown mode: %MODE%
    exit /b 1
)

exit /b 0
