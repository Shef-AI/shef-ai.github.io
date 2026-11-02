::https://github.com/willyd/caffe-builder/blob/master/packages/lmdb/cmake
xcopy /s /y "%RECIPE_DIR%\cmake" "%SRC_DIR%\libraries\liblmdb"
if errorlevel 1 exit 1

:: https://github.com/Alexpux/mingw-w64/blob/master/mingw-w64-crt/misc/getopt.c
:: https://github.com/Alexpux/mingw-w64/blob/master/mingw-w64-headers/crt/getopt.h
xcopy /y "%RECIPE_DIR%\getopt_win" "%SRC_DIR%\libraries\liblmdb\getopt\"
if errorlevel 1 exit 1

cd "%SRC_DIR%\libraries\liblmdb"
mkdir build_release
cd build_release

if %ARCH% == 32 (
    set ARCH_STRING=x86
) else (
    set ARCH_STRING=x64
)

:: Required for ntldd.dll
if %VS_YEAR% == 2008 (
    set "LIB=%LIB%;C:\Program Files (x86)\Windows Kits\8.1\lib\winv6.3\um\%ARCH_STRING%"
)

set "INCLUDE=%INCLUDE%;%SRC_DIR%\libraries\liblmdb\getopt\"

cmake -G"NMake Makefiles" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_PREFIX_PATH="%LIBRARY_PREFIX%" ^
    -DCMAKE_INSTALL_PREFIX="%LIBRARY_PREFIX%" ^
    -DBUILD_SHARED_LIBS=True ^
    -DLMDB_BUILD_TOOLS=True ^
    -DLMDB_BUILD_TESTS=True ^
    ..
if errorlevel 1 exit 1

cmake --build . --config Release
if errorlevel 1 exit 1

ctest -C Release
if errorlevel 1 exit 1

cmake --build . --target install
if errorlevel 1 exit 1