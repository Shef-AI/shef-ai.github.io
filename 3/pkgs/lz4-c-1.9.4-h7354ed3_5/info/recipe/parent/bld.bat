@echo off
setlocal EnableDelayedExpansion

:: Build lz4 shared library using CMake (supports win-64 and win-arm64)
mkdir %SRC_DIR%\build_shared
cd %SRC_DIR%\build_shared
if errorlevel 1 exit 1

cmake -G Ninja ^
    %CMAKE_ARGS% ^
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ^
    -DLZ4_BUILD_CLI=ON ^
    -DLZ4_BUILD_LEGACY_LZ4C=OFF ^
    -DBUILD_SHARED_LIBS=ON ^
    -DBUILD_STATIC_LIBS=OFF ^
    %SRC_DIR%\build\cmake
if errorlevel 1 exit 1

cmake --build . --config Release --parallel %CPU_COUNT%
if errorlevel 1 exit 1

cl.exe /nologo /O2 ^
    /I "%SRC_DIR%\lib" ^
    /I "%SRC_DIR%\programs" ^
    "%SRC_DIR%\programs\datagen.c" ^
    "%SRC_DIR%\tests\datagencli.c" ^
    /Fe:datagen.exe
if errorlevel 1 exit 1

:: Run tests only if not cross-compiling
if not "%CONDA_BUILD_CROSS_COMPILATION%"=="1" (
    echo Running tests...
    lz4 -i1b lz4.exe
    if errorlevel 1 exit 1
    lz4 -i1b5 lz4.exe
    if errorlevel 1 exit 1
    lz4 -i1b10 lz4.exe
    if errorlevel 1 exit 1
    lz4 -i1b15 lz4.exe
    if errorlevel 1 exit 1

    datagen -g0     | lz4 -v     | lz4 -t
    if errorlevel 1 exit 1
    datagen -g16KB  | lz4 -9     | lz4 -t
    if errorlevel 1 exit 1
    datagen         | lz4        | lz4 -t
    if errorlevel 1 exit 1
    datagen -g6M -P99 | lz4 -9BD | lz4 -t
    if errorlevel 1 exit 1
    datagen -g17M   | lz4 -9v    | lz4 -qt
    if errorlevel 1 exit 1
    datagen -g33M   | lz4 --no-frame-crc | lz4 -t
    if errorlevel 1 exit 1
    datagen -g256MB | lz4 -vqB4D | lz4 -t
    if errorlevel 1 exit 1
)

:: Install shared library
cmake --install . --config Release
if errorlevel 1 exit 1

:: windows-output-name.patch builds liblz4.dll/liblz4.lib directly on MSVC.
if not exist "%LIBRARY_BIN%\liblz4.dll" exit 1
if not exist "%LIBRARY_LIB%\liblz4.lib" exit 1
if exist "%LIBRARY_BIN%\lz4.dll" exit 1
if exist "%LIBRARY_LIB%\lz4.lib" exit 1

:: pkg-config template still uses -llz4; Windows links against liblz4.lib.
set "_lz4_pc=%LIBRARY_LIB%\pkgconfig\liblz4.pc"
if exist "%_lz4_pc%" (
    powershell -NoProfile -Command ^
        "(Get-Content -LiteralPath '%_lz4_pc%') -replace '-llz4', '-lliblz4' | Set-Content -LiteralPath '%_lz4_pc%' -Encoding utf8"
    if errorlevel 1 exit 1
)

:: Also build static library (for lz4-c-static output to copy later)
mkdir %SRC_DIR%\build_static
cd %SRC_DIR%\build_static
if errorlevel 1 exit 1

cmake -G Ninja ^
    %CMAKE_ARGS% ^
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ^
    -DLZ4_BUILD_CLI=OFF ^
    -DLZ4_BUILD_LEGACY_LZ4C=OFF ^
    -DBUILD_SHARED_LIBS=OFF ^
    -DBUILD_STATIC_LIBS=ON ^
    %SRC_DIR%\build\cmake
if errorlevel 1 exit 1

cmake --build . --config Release --parallel %CPU_COUNT%
if errorlevel 1 exit 1
