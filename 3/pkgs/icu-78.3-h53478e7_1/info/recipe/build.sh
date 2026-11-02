#!/bin/bash
# Get an updated config.sub and config.guess
cp $BUILD_PREFIX/share/libtool/build-aux/config.* ./source

set -ex

if [[ "${target_platform:-}" == win-* ]]; then
  # MSVC's link.exe must come before MSYS2's coreutils `link` on PATH.
  export PATH="$(dirname "$(which -a link | grep MSVC | head -1)"):$PATH"
  export CXXFLAGS="$CXXFLAGS /std:c++17"
  # Tell ICU's configure we're targeting MSVC (not real MSYS).
  cp source/config/mh-msys-msvc source/config/mh-unknown
  # configure mis-detects EXEEXT="" for *-pc-windows; force .exe back in.
  sed -i.bak 's/EXEEXT=""/EXEEXT=.exe/g' source/configure
  export BUILD=x86_64-pc-windows
  export HOST=x86_64-pc-windows
fi

cd source

chmod +x configure install-sh

# conda-build does not export HOST in native builds and clang_bootstrap has
# no activation script that would set it, so derive it from BUILD.
HOST="${HOST:-${BUILD}}"

if [[ "${target_platform:-}" == osx-* ]]; then
  # clang_bootstrap (used on macOS to keep libxml2/icu out of the build env)
  # does not ship the activation scripts that normally inject
  # -headerpad_max_install_names. ICU's short @rpath/libicu*.dylib install
  # names mean even that flag would only reserve ~40 bytes -- not enough for
  # conda-build to splice in an extra LC_RPATH afterwards. Reserve a fixed
  # 4 KB pad in every Mach-O we link.
  export LDFLAGS="${LDFLAGS:-} -Wl,-headerpad,0x1000"
fi

EXTRA_OPTS=""
if [[ "${target_platform:-}" != win-* ]]; then
  # Static libs are required by our test suite (test -f libicu*.a). On
  # Windows + MSVC, --enable-static breaks data packaging: ICU's data
  # Makefile expects an "out/tmp/dirs.timestamp" rule that only exists in
  # the shared-only build, so adding --enable-static there fails with
  # "No rule to make target 'out/tmp/dirs.timestamp'".
  EXTRA_OPTS="--enable-static"
fi

./configure --prefix="${PREFIX}"  \
            --build=${BUILD}      \
            --host=${HOST}        \
            --disable-samples     \
            --disable-extras      \
            --disable-layout      \
            --disable-tests       \
            ${EXTRA_OPTS}

make -j${CPU_COUNT} ${VERBOSE_CM}
make check
make install

# Remove system utils need only for rebuild custom icu data
rm -rf ${PREFIX}/sbin
