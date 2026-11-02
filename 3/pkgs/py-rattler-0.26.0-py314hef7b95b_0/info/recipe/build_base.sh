#!/bin/bash

set -euxo pipefail

export CARGO_PROFILE_RELEASE_STRIP=symbols
export CARGO_PROFILE_RELEASE_LTO=fat

export OPENSSL_DIR=$PREFIX

# Ref: https://github.com/conda-forge/py-rattler-feedstock/pull/101
# native-tls uses the conda openssl on Linux and Schannel on Windows,
# both of which negotiate TLS 1.3. On macOS it uses Apple's deprecated
# SecureTransport API, which never implemented TLS 1.3, so servers that
# require TLS 1.3 fail with "bad protocol version". Use rustls there,
# which is also what the PyPI wheels ship.
# See: https://github.com/conda/rattler/issues/2749
if [[ "$target_platform" == osx-* ]]; then
  export MATURIN_PEP517_ARGS="--no-default-features --features=rustls"
else
  export MATURIN_PEP517_ARGS="--no-default-features --features=native-tls"
fi

if [[ "$target_platform" == linux-* ]]; then
  export OPENSSL_DIR="$PREFIX"
fi

# Run the maturin build via pip which works for direct and
# cross-compiled builds.
$PYTHON -m pip install . -vv --no-deps --no-build-isolation

pushd py-rattler
cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
