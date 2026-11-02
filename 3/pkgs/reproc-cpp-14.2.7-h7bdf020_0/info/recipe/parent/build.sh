#!/usr/bin/env bash

set -euo pipefail

cmake ${CMAKE_ARGS} -B build-dyn/ \
    -G Ninja \
    -D CMAKE_C_COMPILER=$CC \
    -D CMAKE_CXX_COMPILER=$CXX \
    -D BUILD_SHARED_LIBS=ON \
    -D REPROC++=ON \
    -D REPROC_TEST=OFF

cmake --build build-dyn/ --parallel ${CPU_COUNT} --verbose

cmake ${CMAKE_ARGS} -B build-static/ \
    -G Ninja \
    -D CMAKE_C_COMPILER=$CC \
    -D CMAKE_CXX_COMPILER=$CXX \
    -D BUILD_SHARED_LIBS=OFF \
    -D REPROC++=ON \
    -D REPROC_TEST=OFF

cmake --build build-static/ --parallel ${CPU_COUNT} --verbose
