#! /bin/bash

# Get an updated config.sub and config.guess
cp -r ${BUILD_PREFIX}/share/libtool/build-aux/config.* .

set -e
IFS=$' \t\n' # workaround for conda 4.2.13+toolchain bug

# Adopt a Unix-friendly path if we're on Windows (see bld.bat).
[ -n "$PATH_OVERRIDE" ] && export PATH="$PATH_OVERRIDE"

# On Windows we want $LIBRARY_PREFIX in both "mixed" (C:/Conda/...) and Unix
# (/c/Conda) forms, but Unix form is often "/" which can cause problems.
if [ -n "$LIBRARY_PREFIX_M" ] ; then
    mprefix="$LIBRARY_PREFIX_M"
    if [ "$ARCH" = "32" ]; then
        bprefix="${mprefix/h_env/build_env}"
    else
        bprefix=$mprefix
    fi
    if [ "$LIBRARY_PREFIX_U" = / ] ; then
        uprefix=""
    else
        uprefix="$LIBRARY_PREFIX_U"
    fi
    # these are set for MSVC and make no sense
    unset CFLAGS
    unset CXXFLAGS
else
    mprefix="$PREFIX"
    bprefix="$PREFIX"
    uprefix="$PREFIX"
fi

# On Windows we need to regenerate the configure scripts.
if [ -n "$VS_MAJOR" ] ; then
    am_version=1.15 # keep sync'ed with meta.yaml
    export ACLOCAL=aclocal-$am_version
    export AUTOMAKE=automake-$am_version
    autoreconf_args=(
        --force
        --install
        -I "$bprefix/share/aclocal"
        -I "$bprefix/mingw-w64/share/aclocal" # note: this is correct for win32 also!
    )
    autoreconf "${autoreconf_args[@]}"
fi

export PKG_CONFIG_LIBDIR=$uprefix/lib/pkgconfig:$uprefix/share/pkgconfig:${uprefix/h_env/build_env}/lib/pkgconfig:${uprefix/h_env/build_env}/share/pkgconfig
configure_args=(
    --prefix=$uprefix
    --build="${BUILD}"
    --disable-dependency-tracking
    --disable-selective-werror
    --disable-silent-rules
)
./configure "${configure_args[@]}"
make -j${CPU_COUNT} ${VERBOSE_AT}
make install
make check

rm -rf $uprefix/share/doc/libpthread-stubs
