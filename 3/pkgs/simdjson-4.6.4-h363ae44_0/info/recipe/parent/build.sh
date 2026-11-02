#!/usr/bin/env bash
#
set -euo pipefail

cmake ${CMAKE_ARGS} -B build/ \
    -G Ninja \
    -D SIMDJSON_DEVELOPER_MODE=OFF \
    -D SIMDJSON_BUILD_STATIC_LIB=ON \
    -D BUILD_SHARED_LIBS=ON \
    -D CMAKE_BUILD_TYPE=Release

cmake --build build/ --parallel "${CPU_COUNT}" --verbose

cmake --install  build/
