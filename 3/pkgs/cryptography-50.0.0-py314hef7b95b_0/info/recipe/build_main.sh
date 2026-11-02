#!/bin/bash
set -ex

# As of cryptography version 40.0.0, build instructions have changed: https://cryptography.io/en/latest/changelog/#v40-0-0
# here is the documentation on setting things manually, https://docs.rs/openssl/latest/openssl/#manual
export OPENSSL_DIR=$PREFIX
$PYTHON -m pip install . -vv --no-deps --no-build-isolation
