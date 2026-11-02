@echo off
setlocal enabledelayedexpansion

echo === BUILDING KRB5 WINDOWS ===

REM Always build everything - the file patterns in meta.yaml will determine what gets packaged
echo === BUILDING KRB5 (ALL COMPONENTS) ===

set NO_LEASH=1

REM Finds stdint.h from msinttypes.
set INCLUDE=%LIBRARY_INC%;%INCLUDE%

REM Set the install path
set KRB_INSTALL_DIR=%LIBRARY_PREFIX%

REM Need this set or libs/Makefile fails
set VISUALSTUDIOVERSION=%VS_MAJOR%0

REM Set environment variables like conda-forge
set KRB_INSTALL_DIR=%LIBRARY_PREFIX%

REM Fix perl locale warnings
set LC_ALL=C
set LANG=C

cd src

echo === CREATING MAKEFILE FOR WINDOWS ===
nmake -f Makefile.in prep-windows
if errorlevel 1 (
    echo ERROR: Makefile preparation failed
    exit 1
)

echo === BUILDING SOURCES ===
nmake NODEBUG=1
if errorlevel 1 (
    echo ERROR: Build failed
    exit 1
)

echo === INSTALLING ===
nmake install NODEBUG=1
if errorlevel 1 (
    echo ERROR: Install failed
    exit 1
)

echo === VERIFICATION ===
echo Checking critical installed files:
set ERROR_COUNT=0

REM Check for executables - use PREFIX which should be the correct install location
if exist "%PREFIX%\Library\bin\kinit.exe" (
    echo ✓ kinit.exe found in Library/bin/
) else (
    echo ✗ ERROR: kinit.exe not found
    set /a ERROR_COUNT+=1
)

if exist "%PREFIX%\Library\bin\klist.exe" (
    echo ✓ klist.exe found in Library/bin/
) else (
    echo ✗ ERROR: klist.exe not found
    set /a ERROR_COUNT+=1
)

REM Check for additional executables that should be built
if exist "%PREFIX%\Library\bin\kpasswd.exe" (
    echo ✓ kpasswd.exe found in Library/bin/
) else (
    echo ✗ ERROR: kpasswd.exe not found
    set /a ERROR_COUNT+=1
)

if exist "%PREFIX%\Library\bin\kswitch.exe" (
    echo ✓ kswitch.exe found in Library/bin/
) else (
    echo ✗ ERROR: kswitch.exe not found
    set /a ERROR_COUNT+=1
)

REM Check for DLLs
if exist "%PREFIX%\Library\bin\krb5_64.dll" (
    echo ✓ krb5_64.dll found in Library/bin/
) else (
    echo ✗ ERROR: krb5_64.dll not found
    set /a ERROR_COUNT+=1
)

REM Check for headers
if exist "%PREFIX%\Library\include\krb5.h" (
    echo ✓ krb5.h found in Library/include/
) else (
    echo ✗ ERROR: krb5.h not found
    set /a ERROR_COUNT+=1
)



if %ERROR_COUNT% GTR 0 (
    echo ERROR: %ERROR_COUNT% critical files missing
    exit /b 1
)

echo === BUILD COMPLETE === 
