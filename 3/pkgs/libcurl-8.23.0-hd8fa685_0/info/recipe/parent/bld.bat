@REM Create 'build' directory
mkdir %SRC_DIR%\build
if errorlevel 1 exit 1
pushd %SRC_DIR%\build
if errorlevel 1 exit 1

@REM CMake build type as a variable
@REM We use this information in multiple places
set BUILD_TYPE=Release

@REM MIT Kerberos support;
@REM libkrb5 won't provide 'gssapi/gssapi_generic.h' header on Windows,
@REM refer to the nmake script on the 'krb5' repository for details:
@REM 'krb5@github:src/MakeFile.in'
@REM This file is explicitly checked during curl's CMake configuration step
@REM if CURL_USE_GSSAPI=ON.
@REM CURL_WINDOWS_SSPI is the Windows native equivalent of CURL_USE_GSSAPI
@REM
@REM Tests;
@REM The build script won't generate the CTest fixtures
@REM
@REM Upstream provides a Perl script to run the tests as of v8.18.0
@REM
@REM Other dependencies;
@REM No libnghttp2 and libidn2 on Windows

@REM Configure with CMake
cmake -G "Ninja" ^
    %CMAKE_ARGS% ^
    -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" ^
    -DCMAKE_INSTALL_PREFIX="%LIBRARY_PREFIX%" ^
    -DBUILD_SHARED_LIBS=ON ^
    -DBUILD_STATIC_LIBS=OFF ^
    -DBUILD_TESTING=OFF ^
    -DBUILD_CURL_EXE=ON ^
    -DUSE_NGHTTP2=OFF ^
    -DUSE_LIBIDN2=OFF ^
    -DUSE_WIN32_IDN=OFF ^
    -DCURL_WINDOWS_SSPI=ON ^
    -DCURL_USE_SCHANNEL=ON ^
    -DCURL_USE_LIBSSH2=ON ^
    -DCURL_USE_LIBPSL=OFF ^
    -DCURL_DISABLE_LDAP=ON ^
    -DCURL_ZSTD=ON ^
    -DENABLE_UNICODE=ON ^
    %SRC_DIR%
if errorlevel 1 exit 1

@REM Single step build and install
cmake --build . --config %BUILD_TYPE% --target install --verbose
if errorlevel 1 exit 1

@REM Build script generated 'libcurl_imp.lib', rename to 'libcurl.lib'
@REM Note that this is not the static lib
move %LIBRARY_LIB%\libcurl_imp.lib %LIBRARY_LIB%\libcurl.lib
if errorlevel 1 exit 1

popd
if errorlevel 1 exit 1
