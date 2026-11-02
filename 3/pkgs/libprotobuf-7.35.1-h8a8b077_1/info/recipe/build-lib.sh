#!/bin/bash
set -ex

if [[ "$(uname)" == "Linux" ]]; then
    # protobuf uses PROTOBUF_OPT_FLAG to set the optimization level
    # unit test can fail if optmization above 0 are used.
    CPPFLAGS="${CPPFLAGS//-O[0-9]/}"
    CXXFLAGS="${CXXFLAGS//-O[0-9]/}"
    export PROTOBUF_OPT_FLAG="-O2"
    # to improve performance, disable checks intended for debugging
    CXXFLAGS="$CXXFLAGS -DNDEBUG"
elif [[ "$(uname)" == "Darwin" ]]; then
    # Do NOT add -D_LIBCPP_DISABLE_AVAILABILITY here. With clang 20 / libcxx-devel
    # that forces bad_function_call's key function into the dylib; macOS 12.1's
    # system libc++ does not provide those LLVM 19+ symbols, so shared linking
    # fails with undefined std::bad_function_call (~, typeinfo, vtable).
    # remove pie from LDFLAGS
    LDFLAGS="${LDFLAGS//-pie/}"
    # CoreFoundation is needed as least as of libprotobuf>=4.23.X
    LDFLAGS="${LDFLAGS} -framework CoreFoundation"
fi

# required to pick up conda installed zlib; ensure UPB symbols are visible, see
# https://github.com/protocolbuffers/protobuf/blob/v29.1/upb/port/def.inc#L69-L91
export CPPFLAGS="${CPPFLAGS} -I${PREFIX}/include -DUPB_BUILD_API"
export LDFLAGS="${LDFLAGS} -L${PREFIX}/lib"

# delete vendored gtest to force protobuf_USE_EXTERNAL_GTEST to work;
# this gets run twice (second time for libprotobuf-static), so don't fail
rm -rf ./third_party/googletest | true

if [[ "$PKG_NAME" == "libprotobuf-static" ]]; then
    export CF_SHARED=OFF
    export CF_TESTS=OFF
    mkdir build-static
    cd build-static
else
    export CF_SHARED=ON
    export CF_TESTS=ON
    mkdir build-shared
    cd build-shared

    if [[ "$CONDA_BUILD_CROSS_COMPILATION" == 1 ]]; then
        export CF_TESTS=OFF
    fi
fi

cmake -G "Ninja" \
    ${CMAKE_ARGS} \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=17 \
    -Dprotobuf_ABSL_PROVIDER="package" \
    -Dprotobuf_BUILD_LIBUPB=ON \
    -Dprotobuf_BUILD_SHARED_LIBS=$CF_SHARED \
    -Dprotobuf_BUILD_TESTS=$CF_TESTS \
    -Dprotobuf_JSONCPP_PROVIDER="package" \
    -Dprotobuf_USE_EXTERNAL_GTEST=ON \
    -Dprotobuf_WITH_ZLIB=ON \
    ..

cmake --build .

if [[ "$CF_TESTS" == "ON" ]]; then
    ctest --progress --output-on-failure
fi

cmake --install .
