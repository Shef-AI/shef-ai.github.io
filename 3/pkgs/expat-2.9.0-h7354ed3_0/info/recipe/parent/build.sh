#!/bin/bash

# Configure using CMake
cmake -G "Ninja" \
      $CMAKE_ARGS \
      -DEXPAT_BUILD_TOOLS=ON \
      -DEXPAT_BUILD_PKGCONFIG=ON \
      -DEXPAT_BUILD_TESTS=ON \
      -DEXPAT_BUILD_EXAMPLES=OFF \
      -DEXPAT_BUILD_DOCS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_INSTALL_PREFIX=$PREFIX \
      -S $SRC_DIR \
      -B build

# Build and install
cmake --build build --config Release --parallel $CPU_COUNT --target install

# Run tests
ctest -C Release --test-dir build
