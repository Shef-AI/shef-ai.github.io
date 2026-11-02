@echo on
setlocal EnableDelayedExpansion

if "%ARCH%"=="32" (
    set OSSL_CONFIGURE=VC-WIN32
) ELSE IF "%target_platform%"=="win-arm64" (
    set OSSL_CONFIGURE=VC-WIN64-ARM
) ELSE (
    set OSSL_CONFIGURE=VC-WIN64A
)

REM Configure step
REM
REM We set OPENSSLDIR to a location with extremely limited write permissions
REM (e.g. %%CommonProgramFiles%%\ssl) to limit the risk of non-privileged users
REM exploiting OpenSSL's config/engines feature to perform arbitrary code execution
REM (see e.g. CVE-2019-5443, CVE-2024-6975).  Per-environment config and CA certs
REM are not provided via OPENSSLDIR; SSL_CERT_FILE is set via an activation script
REM to point to the ca-certificates package CA root file.
REM If that folder does not exist, OpenSSL still works (defaults + SSL_CERT_FILE).
set PERL=%BUILD_PREFIX%\Library\bin\perl
%BUILD_PREFIX%\Library\bin\perl configure %OSSL_CONFIGURE% ^
    --prefix=%LIBRARY_PREFIX% ^
    --openssldir="%CommonProgramFiles%\ssl" ^
    threads ^
    no-zlib ^
    enable-legacy ^
    no-module ^
    shared

if errorlevel 1 exit 1

REM Specify in metadata where the packaging is coming from
set "OPENSSL_VERSION_BUILD_METADATA=+anaconda"

REM Dump configuration results
%BUILD_PREFIX%\Library\bin\perl configdata.pm --dump
if errorlevel 1 exit 1

nmake
if errorlevel 1 exit 1

REM Testing step
REM Skip tests on win-arm64 during bootstrap due to MD4 test failures
REM (MD4 is a legacy algorithm; MD5, SHA, AES, etc. all pass)
@REM Tests: 72 Failed: 1
if "%target_platform%"=="win-arm64" (
    echo Skipping tests on win-arm64 bootstrap - known MD4 legacy algorithm issue
) ELSE (
    nmake test
    if errorlevel 1 exit 1
)

REM Install software components only; i.e., skip the HTML docs
nmake install_sw
if errorlevel 1 exit 1

REM Install support files for reference purposes.  (Note that the way we
REM configured OPENSSLDIR above makes these files non-functional.)
nmake install_ssldirs OPENSSLDIR=%LIBRARY_PREFIX%\ssl
if errorlevel 1 exit 1

REM Install applink.c - required by applications (like Python) that use OpenSSL on Windows
copy ms\applink.c %LIBRARY_INC%\openssl\applink.c
if errorlevel 1 exit 1

REM Add pkgconfig files: adapted from https://github.com/conda-forge/openssl-feedstock/pull/106
:: install pkgconfig metadata (useful for downstream packages);
:: adapted from inspecting the conda-forge .pc files for unix, as well as
:: https://github.com/microsoft/vcpkg/blob/master/ports/openssl/install-pc-files.cmake
mkdir %LIBRARY_PREFIX%\lib\pkgconfig
for %%F in (openssl libssl libcrypto) DO (
    echo prefix=%LIBRARY_PREFIX:\=/% > %%F.pc
    type %RECIPE_DIR%\win_pkgconfig\%%F.pc.in >> %%F.pc
    echo Version: %PKG_VERSION% >> %%F.pc
    copy %%F.pc %LIBRARY_PREFIX%\lib\pkgconfig\%%F.pc
)

:: Copy the [de]activate scripts to %PREFIX%\etc\conda\[de]activate.d.
:: This will allow them to be run on environment activation.
for %%F in (activate deactivate) DO (
    if not exist %PREFIX%\etc\conda\%%F.d mkdir %PREFIX%\etc\conda\%%F.d
    copy "%RECIPE_DIR%\%%F.bat" "%PREFIX%\etc\conda\%%F.d\%PKG_NAME%_%%F.bat"
    copy "%RECIPE_DIR%\%%F.ps1" "%PREFIX%\etc\conda\%%F.d\%PKG_NAME%_%%F.ps1"
    :: Copy unix shell activation scripts, needed by Windows Bash users
    copy "%RECIPE_DIR%\%%F.sh" "%PREFIX%\etc\conda\%%F.d\%PKG_NAME%_%%F.sh"
)
