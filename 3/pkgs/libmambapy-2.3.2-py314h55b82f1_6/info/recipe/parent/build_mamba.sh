#!/bin/bash

set -euxo pipefail

export CXXFLAGS="${CXXFLAGS}"

if [[ $PKG_NAME == "libmamba" ]]; then

    cmake -B build-lib/ \
        -G Ninja \
        ${CMAKE_ARGS} \
        -D CMAKE_INSTALL_PREFIX=$PREFIX  \
        -D CMAKE_PREFIX_PATH=$PREFIX     \
        -D CMAKE_BUILD_TYPE=Release      \
        -D BUILD_SHARED=ON \
        -D BUILD_LIBMAMBA=ON \
        -D BUILD_MAMBA_PACKAGE=ON \
        -D BUILD_LIBMAMBAPY=OFF \
        -D BUILD_MAMBA=OFF \
        -D BUILD_MICROMAMBA=OFF \
        -D MAMBA_WARNING_AS_ERROR=OFF
    cmake --build build-lib/ --parallel ${CPU_COUNT}
    cmake --install build-lib/

elif [[ $PKG_NAME == "libmambapy" ]]; then
    export CMAKE_ARGS="-G Ninja"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # skbuild considers that only the major version is important for the deployment target
        # https://github.com/scikit-build/scikit-build/blob/main/skbuild%2Fconstants.py#L92-L94
        export CMAKE_ARGS="${CMAKE_ARGS} -DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET%.*}.0"
    fi
    "${PYTHON}" -m pip install --no-deps --no-build-isolation --config-settings="--build-type=Release" --config-settings="--generator=Ninja" -vv ./libmambapy

fi