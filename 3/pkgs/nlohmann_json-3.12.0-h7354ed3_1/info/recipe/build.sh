#!/bin/bash

cmake -G "Ninja" \
    -DCMAKE_INSTALL_PREFIX=$PREFIX \
    $SRC_DIR \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DJSON_BuildTests=OFF \
    -DJSON_MultipleHeaders=ON \
    ${CMAKE_ARGS}
ninja install
