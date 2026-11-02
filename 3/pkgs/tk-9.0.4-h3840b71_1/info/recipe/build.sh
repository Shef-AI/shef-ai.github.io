#!/bin/bash

IFS="." read -a VER_ARR <<<"${PKG_VERSION}"

ARCH_FLAG=""
if [[ ${ARCH} == 64 || ${ARCH} == s390x ]]; then
    ARCH_FLAG="--enable-64bit"
fi

# XXX --disable-zipfs -- we don't want zip archives tacked on the end
# of dynamic libraries!
#
# However, the bootstrap from 8.* to 9.* has two problems.  Firstly,
# the zipfs code in configure (in pkgs/thread) during make wants to
# use a tclsh 9 but the only parts we have are in tcl9.0.4/unix (both
# tclsh and its shared library).  For macOS we can't export DYLD_*
# values as SIP-aware binaries (notably /bin/bash in the guise of
# tcl9.0.4/pkgs/thread3.0.6/configure) won't inherit them.
#
# Secondly, that configure code in thread3.0.6 is broken anyway as it
# doesn't initialize ZIPFS_BUILD to a value it tests for so even when
# you specify --disable-zipfs it tries to run the enabling code (which
# requires tclsh 9, as above).  This is fixed in
# https://core.tcl-lang.org/thread/info/db215a0bedcfb697 (late June
# 2026).  aka
# https://github.com/tcltk/thread/commit/4ba68414d0fb9b310143c86251bfe432ff165d35
#
# We can add that as a patch here
#
# Ultimately, in the bootstrap 8->9 case, we would want to make and
# install a tclsh v9 without zipfs in order that we could make a tclsh
# v9 with zipfs
#
# But, the zipfs code will add a zip archive to the end of the Tk
# dynamic library.  That is fatal for conda packaging (as
# install_name_tool complains that the physical file is longer than
# the internally recorded file extents so cannot work on macOS) but we
# don't want to be distributing modifiable files (I think they're
# meant to be read-only) to users who may not have write access.  (Do
# you really want a modifiable dynamic object?)

pushd tcl${PKG_VERSION}/unix

  ./configure  --prefix="${PREFIX}"  \
               --host=${HOST}        \
               --disable-zipfs       \
               ${ARCH_FLAG}

  make -j${CPU_COUNT} ${VERBOSE_AT}
  make install install-private-headers
popd

pushd tk${PKG_VERSION}/unix
  # autoreconf -vfi
  ./configure --prefix="${PREFIX}"        \
              --host=${HOST}              \
              --with-tcl="${PREFIX}"/lib  \
              --enable-aqua=yes           \
              --disable-zipfs             \
              ${ARCH_FLAG}
  make -j${CPU_COUNT} ${VERBOSE_AT}
  make install
popd

rm -rf "${PREFIX}"/{man,share}

# Link binaries to non-versioned names to make them easier to find and use.
ln -s "${PREFIX}"/bin/tclsh${VER_ARR[0]}.${VER_ARR[1]} "${PREFIX}"/bin/tclsh
ln -s "${PREFIX}"/bin/wish${VER_ARR[0]}.${VER_ARR[1]} "${PREFIX}"/bin/wish

# copy headers
cp "${SRC_DIR}"/tk${PKG_VERSION}/{unix,macosx,generic}/*.h "${PREFIX}"/include/
