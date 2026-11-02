#!/bin/bash

set -e

cd install

find . -type f -exec bash -c 'mkdir -p /$(dirname {}) && cp {} /{}' ';'

export TARGET="${triplet}"

if [[ "${target_platform}" == win-* ]]; then
  EXEEXT=".exe"
  PREFIX=${PREFIX}/Library
  symlink="cp"
else
  symlink="ln -s"
fi

SYSROOT=${PREFIX}/${TARGET}

mkdir -p ${PREFIX}/bin
mkdir -p ${SYSROOT}/bin

TOOLS="addr2line ar c++filt elfedit nm objcopy objdump ranlib readelf size strings strip"
if [[ "${cross_target_platform}" != "osx-"* ]]; then
  TOOLS="${TOOLS} as gprof ld.bfd"
fi
if [[ "${cross_target_platform}" == "win-"* ]]; then
  TOOLS="${TOOLS} dlltool dllwrap windmc windres"
fi

# Remove hardlinks and replace them by softlinks
for tool in ${TOOLS}; do
  tool=${tool}${EXEEXT}
  if [[ "$target_platform" == "$cross_target_platform" ]]; then
      mv ${PREFIX}/bin/${tool} ${PREFIX}/bin/${TARGET}-${tool}
  fi
  rm -rf ${SYSROOT}/bin/${tool}
  $symlink ${PREFIX}/bin/${TARGET}-${tool} ${SYSROOT}/bin/${tool}
done

rm ${PREFIX}/bin/ld${EXEEXT} || true;
rm ${PREFIX}/bin/${TARGET}-ld${EXEEXT} || true;
rm ${SYSROOT}/bin/ld${EXEEXT} || true;

