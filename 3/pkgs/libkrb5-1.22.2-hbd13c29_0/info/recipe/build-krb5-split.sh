#!/bin/bash
set -e

# Always build everything - the file patterns in meta.yaml will determine what gets packaged
echo "=== BUILDING KRB5 (ALL COMPONENTS) ==="

echo "=== BUILDING KRB5 ==="

# Set up environment variables
export CPPFLAGS="${CPPFLAGS/-DNDEBUG/} -I${PREFIX}/include"
export LDFLAGS="${LDFLAGS} -L${PREFIX}/lib"

if [[ ${HOST} =~ .*linux.* ]]; then
  export LDFLAGS="$LDFLAGS -Wl,--disable-new-dtags"
fi

# https://github.com/conda-forge/bison-feedstock/issues/7
export M4="${BUILD_PREFIX}/bin/m4"

echo "=== CONFIGURING KRB5 ==="

# Verify source directory exists
if [[ ! -d "src" ]]; then
    echo "ERROR: src directory not found"
    exit 1
fi

pushd src
  echo "Running autoreconf..."
  autoreconf -i
  
  echo "Running configure..."
  ./configure --prefix=${PREFIX} \
              --host=${HOST} \
              --build=${BUILD} \
              --sysconfdir=${PREFIX}/etc \
              --localstatedir=${PREFIX}/var \
              --runstatedir=${PREFIX}/var/run \
              --without-readline \
              --with-libedit \
              --with-crypto-impl=openssl \
              --with-tls-impl=openssl \
              --without-system-verto \
              --disable-rpath \
              --enable-shared \
              --disable-static \
              --enable-dns-for-realm \
              --with-lmdb \
              --without-ldap
  
  echo "=== BUILDING KRB5 ==="
  echo "Running make with ${CPU_COUNT:-1} jobs..."
  make -j${CPU_COUNT:-1} ${VERBOSE_AT}
  
  echo "=== INSTALLING KRB5 ==="
  echo "Running make install..."
  make install
popd

# Remove man pages to save space
rm -rf "${PREFIX}/share/man"

echo "=== VERIFICATION ==="
echo "Checking critical installed files:"
CRITICAL_FILES=(
    "lib/libkrb5${SHLIB_EXT}"
    "include/krb5.h"
    "include/gssapi.h"
    "bin/kinit"
    "bin/klist"
    "bin/krb5-config"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [[ -f "${PREFIX}/${file}" ]]; then
        echo "✓ ${file} found"
    else
        echo "✗ ERROR: ${file} not found"
        exit 1
    fi
done

echo "=== BUILD COMPLETE ===" 
