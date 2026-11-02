#!/bin/bash
set -euo pipefail

mkdir -p "${PREFIX}/lib"
pushd "${PREFIX}/lib"

# These are compatibility links only. The real libomp files are provided by
# llvm-openmp when an environment selects the LLVM OpenMP runtime.
if [[ "${target_platform}" == osx-* ]]; then
  rm -f libgomp.*dylib
  ln -sf libomp.dylib libgomp.1.dylib
  ln -sf libomp.dylib libgomp.dylib
else
  rm -f libgomp.so.1
  ln -sf libomp.so libgomp.so.1
fi

ls -lah libgomp*

popd
