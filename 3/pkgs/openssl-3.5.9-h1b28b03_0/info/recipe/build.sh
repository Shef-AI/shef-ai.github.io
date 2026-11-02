#!/bin/bash

# Use perl from conda's env
PERL="${BUILD_PREFIX}/bin/perl"

# Array of options for the openssl configurator perl script
declare -a _CONFIG_OPTS

# Organize artifacts within conda file
_CONFIG_OPTS+=(--prefix=${PREFIX})
_CONFIG_OPTS+=(--libdir=lib)

# Create a library that is suitable for multithreaded applications
_CONFIG_OPTS+=(threads)

# Don't compile support for zlib compression.
# Using compression is not recommended for security reasons.
# Ref: https://nvd.nist.gov/vuln/detail/CVE-2012-4929
_CONFIG_OPTS+=(no-zlib)

# Necessary to support some function in Python package cryptography.
# Enabled by default anyway, keeping for explicitness
_CONFIG_OPTS+=(enable-legacy)

# Engines are deprecated from 3.0. Ref: https://github.com/openssl/openssl/blob/openssl-3.5.5/README-ENGINES.md
# With no-module, the legacy provider is built into libcrypto.
_CONFIG_OPTS+=(no-module)

# Ensure that shared libraries are built
_CONFIG_OPTS+=(shared)

if [[ "$target_platform" = "linux-"* ]]; then
  # KTLS is an optimization feature for Linux (and FreeBSD)
  _CONFIG_OPTS+=(enable-ktls)
fi

# NOTE 1: In previous versions of build.sh, no-ssl2 and no-ssl3 were also added.
#   However, ssl2 was removed in OpenSSL 1.1.0 and ssl3 is disabled by default.
# NOTE 2: CF ignores 'fips' but it's off by default anyway.
# NOTE 3: We do not set --openssldir here (unlike Windows in bld.bat). On Unix, conda
#   performs prefix replacement in binaries, so the default OPENSSLDIR (under
#   prefix) is rewritten at install time and the package's ssl dir is used.  The
#   env is user-owned, so the engine-injection risk that motivates a read-only
#   OPENSSLDIR on Windows does not apply.

# Do not allow config to make any guesses based on uname.
# Target names can be found in upstream at Configurations/10-main.conf
_CONFIGURATOR="perl ./Configure"
case "$target_platform" in
  linux-64)
    _CONFIG_OPTS+=(linux-x86_64)
    CFLAGS="${CFLAGS} -Wa,--noexecstack"
    ;;
  linux-aarch64)
    _CONFIG_OPTS+=(linux-aarch64)
    CFLAGS="${CFLAGS} -Wa,--noexecstack"
    ;;
  osx-arm64)
    _CONFIG_OPTS+=(darwin64-arm64-cc)
    ;;
esac

# If build with additional debug flags are needed (e.g. for investigating
# ABI compatibility with abi-dumper), uncomment:
# CFLAGS="${CFLAGS} -Og -g"
CC="${CC}" CFLAGS="${CFLAGS}" CPPFLAGS="${CPPFLAGS}" LDFLAGS="${LDFLAGS}" \
  ${_CONFIGURATOR} "${_CONFIG_OPTS[@]}"

# Specify in metadata where the packaging is coming from
export OPENSSL_VERSION_BUILD_METADATA="+anaconda"

# Dump configuration results
perl configdata.pm --dump

make -j${CPU_COUNT}
make test
make install_sw install_ssldirs
