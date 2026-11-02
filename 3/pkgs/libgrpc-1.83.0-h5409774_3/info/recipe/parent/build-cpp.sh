#!/bin/bash
set -ex

export CMAKE_ARGS="${CMAKE_ARGS} -DCMAKE_CXX_STANDARD=17"

mkdir -p build-cpp
pushd build-cpp

# sanity-check that encapsulation above worked
echo CC="${CC}"
echo CFLAGS="${CFLAGS}"

# point to right protoc
export CMAKE_ARGS="${CMAKE_ARGS} -DProtobuf_PROTOC_EXECUTABLE=$PREFIX/bin/protoc"

cmake -GNinja \
      ${CMAKE_ARGS} \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
      -DCMAKE_PREFIX_PATH=$PREFIX \
      -DCMAKE_INSTALL_PREFIX=$PREFIX \
      -DgRPC_CARES_PROVIDER="package" \
      -DgRPC_PROTOBUF_PROVIDER="package" \
      -DgRPC_SSL_PROVIDER="package" \
      -DgRPC_ZLIB_PROVIDER="package" \
      -DgRPC_ABSL_PROVIDER="package" \
      -DgRPC_RE2_PROVIDER="package" \
      -DProtobuf_ROOT=$PREFIX \
      -DGRPC_RE2_LIBRARY="${PREFIX}/lib/libre2.${SHLIB_EXT}" \
      ..

ninja install
popd
