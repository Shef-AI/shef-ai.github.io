#!/bin/bash
set -x

TARGET="${triplet}"

if [[ "${target_platform}" == win-* ]]; then
  EXEEXT=".exe"
  PREFIX=${PREFIX}/Library
fi

TOOLS="addr2line ar c++filt elfedit nm objcopy objdump ranlib readelf size strings strip"
if [[ "${cross_target_platform}" != "osx-"* ]]; then
  TOOLS="${TOOLS} as gprof ld ld.bfd"
fi
if [[ "${cross_target_plaform}" == "win-"* ]]; then
  TOOLS="${TOOLS} dlltool dllwrap windmc windres"
fi

for tool in ${TOOLS}; do
  if [[ "$target_platform" == "win-"* ]]; then
    cp ${PREFIX}/bin/${TARGET}-${tool}${EXEEXT} ${PREFIX}/bin/${tool}${EXEEXT}
  else
    rm ${PREFIX}/bin/${TARGET}-${tool}${EXEEXT}
    touch ${PREFIX}/bin/${TARGET}-${tool}${EXEEXT}
    ln -s ${PREFIX}/bin/${TARGET}-${tool}${EXEEXT} ${PREFIX}/bin/${tool}${EXEEXT}
  fi
done
