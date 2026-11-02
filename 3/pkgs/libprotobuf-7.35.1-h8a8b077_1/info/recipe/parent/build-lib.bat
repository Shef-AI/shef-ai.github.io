@echo on

if "%PKG_NAME%"=="libprotobuf-static" (
    set CF_SHARED=OFF
    set CF_TESTS=OFF
    mkdir build-static
    cd build-static
) else (
    set CF_SHARED=ON
    set CF_TESTS=ON
    mkdir build-shared
    cd build-shared
)

:: Configure and install based on protobuf's instructions and other `bld.bat`s.
cmake -G "Ninja" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_CXX_STANDARD=17 ^
    -DCMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    -DCMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
    -Dprotobuf_ABSL_PROVIDER="package" ^
    -Dprotobuf_BUILD_LIBUPB=ON ^
    -Dprotobuf_BUILD_SHARED_LIBS=%CF_SHARED% ^
    -Dprotobuf_BUILD_TESTS=%CF_TESTS% ^
    -Dprotobuf_JSONCPP_PROVIDER="package" ^
    -Dprotobuf_MSVC_STATIC_RUNTIME=OFF ^
    -Dprotobuf_USE_EXTERNAL_GTEST=ON ^
    -Dprotobuf_WITH_ZLIB=ON ^
    ..
if %ERRORLEVEL% neq 0 exit 1

cmake --build .
if %ERRORLEVEL% neq 0 exit 1

if "%PKG_NAME%"=="libprotobuf" (
    ctest --progress --output-on-failure
    if %ERRORLEVEL% neq 0 exit 1
)

cmake --install .
if %ERRORLEVEL% neq 0 exit 1
