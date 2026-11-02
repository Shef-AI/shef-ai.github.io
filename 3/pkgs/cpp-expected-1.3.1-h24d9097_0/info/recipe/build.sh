#!/bin/bash

# Isolate the build.
mkdir -p Build
cd Build || exit 1

# Generate the build files.
cmake .. -G"Ninja" ${CMAKE_ARGS} \
    -DCMAKE_PREFIX_PATH=$PREFIX \
    -DCMAKE_INSTALL_PREFIX=$PREFIX \
	-DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_BUILD_TYPE=Release

# Build.
ninja || exit 1

# Run tests.
./tl-expected-tests || exit 1

# Build and install.
ninja install || exit 1
