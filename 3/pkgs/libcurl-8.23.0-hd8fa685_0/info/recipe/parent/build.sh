#!/bin/bash
set -ex

# Create 'build' directory
mkdir -p build || true
pushd build

export CFLAGS="$CFLAGS $CPPFLAGS"

# CMake build type as a variable
export BUILD_TYPE="Release"

if [[ "$target_platform" == "osx-"* ]]; then
    SSL_OPTIONS="-DCURL_USE_OPENSSL=ON -DCURL_USE_SECTRANSP=ON"
else
    SSL_OPTIONS="-DCURL_USE_OPENSSL=ON"
fi

# Tests;
# The build script won't generate the CTest fixtures
# Upstream provides a Perl script to run the tests as of v8.18.0

# Configure with CMake
cmake \
    -DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
    -DCMAKE_INSTALL_PREFIX=${PREFIX} \
    -DBUILD_SHARED_LIBS=ON \
    -DBUILD_STATIC_LIBS=OFF \
    -DBUILD_TESTING=OFF \
    -DBUILD_CURL_EXE=ON \
    -DUSE_NGHTTP2=ON \
    -DCURL_CA_BUNDLE=${PREFIX}/ssl/cacert.pem \
    ${SSL_OPTIONS} \
    -DCURL_USE_LIBPSL=OFF \
    -DCURL_DISABLE_LDAP=ON \
    -DCURL_ZSTD=ON \
    -DCURL_USE_GSSAPI=ON \
    -DCURL_USE_LIBSSH2=ON \
    ..

# Build and install in a single step
cmake --build . --config ${BUILD_TYPE} --parallel ${CPU_COUNT} --target install --verbose

popd
