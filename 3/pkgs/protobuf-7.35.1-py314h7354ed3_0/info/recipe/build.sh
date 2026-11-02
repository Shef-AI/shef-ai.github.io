#!/bin/bash
set -ex

# Workaround missing leading whitespace for mcpu stripping in bazel-toolchain
export CFLAGS=" ${CFLAGS}"
export CXXFLAGS=" ${CXXFLAGS}"
# Re-add Python include path lost by overwriting CFLAGS above
export CFLAGS="${CFLAGS} -I${PREFIX}/include/python${PY_VER}"

source gen-bazel-toolchain

if [[ "${target_platform}" == linux-* ]]; then
  $RECIPE_DIR/add_py_toolchain.sh
  EXTRA_BAZEL_ARGS="--extra_toolchains=//py_toolchain:py_toolchain"
fi

cd python

export PROTOC=$PREFIX/bin/protoc
if [[ "$build_platform" != "$target_platform" ]]; then
    export PROTOC=$BUILD_PREFIX/bin/protoc
fi

export PYTHON_BIN_PATH=$PREFIX/bin/python

# Prevent build_env python from being picked up.
# $BUILD_PREFIX/bin is listed first in PATH, and bazel finds that python first.
export PATH="$PREFIX/bin:${PATH}"

# Hacky workaround to fix some dependency issues with bazel
for f in dist/BUILD.bazel dist/dist.bzl; do
  sed -i '/@system_python\/\/:version\.bzl/d' $f
  sed -i "s|SYSTEM_PYTHON_VERSION|\"${PY_VER//./}\"|g" $f
done
# protobuf misuses `SUPPORTED_PYTHON_VERSIONS[-1]` to mean "default python", see
# https://github.com/protocolbuffers/protobuf/issues/22313
sed -i "s|SUPPORTED_PYTHON_VERSIONS\[-1\]|\"${PY_VER}\"|g" ../MODULE.bazel

bazel build \
    --platforms=//bazel_toolchain:target_platform \
    --host_platform=//bazel_toolchain:build_platform \
    --extra_toolchains=//bazel_toolchain:cc_cf_toolchain \
    --extra_toolchains=//bazel_toolchain:cc_cf_host_toolchain \
    --crosstool_top=//bazel_toolchain:toolchain \
    ${EXTRA_BAZEL_ARGS:-} \
    --cpu=${TARGET_CPU} \
    --local_cpu_resources=${CPU_COUNT} \
    --spawn_strategy=standalone \
    //python/dist:binary_wheel

$PYTHON -m pip install --no-deps --no-build-isolation ../bazel-bin/python/dist/protobuf-${PKG_VERSION}-*.whl

# Remove chance of trying to install multiple variants.
rm ../bazel-bin/python/dist/protobuf-${PKG_VERSION}-*.whl
