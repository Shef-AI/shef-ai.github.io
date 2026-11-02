#!/usr/bin/env sh

set -euxo pipefail

# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/libtool/build-aux/config.* ./build-aux
cp $BUILD_PREFIX/share/libtool/build-aux/config.* ./libcharset/build-aux

./configure --prefix=${PREFIX}  \
            --host=${HOST}      \
            --build=${BUILD}    \
            --enable-static     \
            --disable-rpath     \
            --enable-extra-encodings

if [[ "${target_platform}" == osx-* ]]; then
    make -f Makefile.devel CC="${CC_FOR_BUILD}" CFLAGS="${CFLAGS}"
fi

make -j${CPU_COUNT}
