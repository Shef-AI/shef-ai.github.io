#!/bin/bash
set -euxo pipefail

# Pip check
$PYTHON -m pip check

# Verify launcher files are present on macOS
if [[ "$(uname)" == "Darwin" ]]; then
    SP_DIR="$(python -c 'import site; print(site.getsitepackages()[0])')"
    test -f "${SP_DIR}/menuinst/data/appkit_launcher_arm64"
    test -f "${SP_DIR}/menuinst/data/appkit_launcher_x86_64"
    test -f "${SP_DIR}/menuinst/data/osx_launcher_arm64"
    test -f "${SP_DIR}/menuinst/data/osx_launcher_x86_64"
fi

# PBP runs conda-build under a separate "tst" prefix; CONDA_EXE may still
# point at that broken tooling conda. Point menuinst at the test env's conda.
if [[ -x "${CONDA_PREFIX}/bin/conda" ]]; then
  export CONDA_EXE="${CONDA_PREFIX}/bin/conda"
elif [[ -x "${CONDA_PREFIX}/condabin/conda" ]]; then
  export CONDA_EXE="${CONDA_PREFIX}/condabin/conda"
fi
export CONDA_ROOT_PREFIX="${CONDA_PREFIX}"

# Run tests
# Cannot run tests in test_schema.py because hypothesis-jsonschema is not on defaults
# Cannot run others because privilege elevation is not possible on the build platform
pytest tests/ -vvv --ignore=tests/test_schema.py --ignore=tests/test_elevation.py