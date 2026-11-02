#!/bin/bash

unset LD

if [[ "$target_platform" == "linux-"* ]]; then
  export CC=${GCC}
  export CXX=${GXX}
fi

export CXXFLAGS="${CXXFLAGS} ${LDFLAGS}"
export CFLAGS="${CFLAGS} ${LDFLAGS}"

./configure --prefix=$PREFIX --disable-static --disable-doc
make -j$CPU_COUNT
make install

if [[ "${CONDA_BUILD_CROSS_COMPILATION:-}" != "1" || "${CROSSCOMPILING_EMULATOR}" != "" ]]; then
  make check
fi
