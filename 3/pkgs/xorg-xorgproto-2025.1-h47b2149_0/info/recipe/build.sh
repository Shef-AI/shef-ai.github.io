#! /bin/bash
set -e

cp -f "$BUILD_PREFIX/share/gnuconfig/config."{sub,guess} .

export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig"
configure_args=(
    --prefix="$PREFIX"
    --disable-dependency-tracking
    --disable-silent-rules
)
./configure "${configure_args[@]}"
make -j"$CPU_COUNT"
make install

if [[ "${CONDA_BUILD_CROSS_COMPILATION:-}" != "1" || "${CROSSCOMPILING_EMULATOR}" != "" ]]; then
    make check
fi
