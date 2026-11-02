#!/bin/bash

set -e

TARGET="${triplet}"

if [[ "$target_platform" == win-* ]]; then
  EXEEXT=".exe"
  PREFIX=$PREFIX/Library
  symlink="cp"
else
  symlink="ln -s"
fi

SYSROOT=$PREFIX/${TARGET}

mkdir -p $PREFIX/bin
mkdir -p $SYSROOT/bin

if [[ "$target_platform" == "$cross_target_platform" ]]; then
  cp $PWD/install/$PREFIX/bin/ld${EXEEXT} $PREFIX/bin/$TARGET-ld${EXEEXT}
else
  cp $PWD/install/$PREFIX/bin/$TARGET-ld${EXEEXT} $PREFIX/bin/$TARGET-ld${EXEEXT}
fi

$symlink $PREFIX/bin/$TARGET-ld${EXEEXT} $SYSROOT/bin/ld${EXEEXT}
