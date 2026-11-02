#!/bin/bash
set -ex

# Compile a trivial service definition to C++
if [[ "${build_platform}" == "${target_platform}" ]]; then
  protoc -I. --plugin=protoc-gen-grpc=$PREFIX/bin/grpc_cpp_plugin --grpc_out=. hello.proto
  test -f hello.grpc.pb.h
  test -f hello.grpc.pb.cc
fi

# taken from cd examples/cpp/helloworld
cd examples/cpp/helloworld

# folder already contains a file called BUILD
mkdir build-cpp
cd build-cpp

# abseil's ABI is sensitive to this symbol, and for some reason, grpc
# doesn't pick it up from the CPPFLAGS in our compiler activation; see
# https://github.com/abseil/abseil-cpp/issues/1624
CXXFLAGS="${CXXFLAGS} -DNDEBUG"

cmake -G "Ninja" \
    -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_PREFIX_PATH="$PREFIX" \
    -DCMAKE_MODULE_PATH="$PREFIX/lib/cmake" \
    ..

cmake --build .
