@echo on
set "PYO3_PYTHON=%PYTHON%"

:: Use CMake to build aws-lc-sys; more reliable than the default cc-crate
:: builder in conda's Windows toolchain environment.
set AWS_LC_SYS_CMAKE_BUILDER=1
:: Jitter entropy module requires intrinsics headers not available in the
:: conda build env; safe to disable on Windows where BCryptGenRandom provides
:: OS-level entropy.
set AWS_LC_SYS_NO_JITTER_ENTROPY=1
set CARGO_PROFILE_RELEASE_STRIP=symbols
set CARGO_PROFILE_RELEASE_LTO=fat

set "CMAKE_GENERATOR=NMake Makefiles"
maturin build -v --jobs 1 --release --strip --manylinux off --interpreter=%PYTHON% --no-default-features --features=native-tls
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

cd py-rattler

FOR /F "delims=" %%i IN ('dir /s /b target\wheels\*.whl') DO set py_rattler_wheel=%%i
%PYTHON% -m pip install %py_rattler_wheel% -vv --no-deps --no-build-isolation
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
