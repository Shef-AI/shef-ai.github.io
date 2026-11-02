

set -ex



bash ./test-abseil-libs.sh libabseil
cd cmake_test
export CMAKE_ARGS="$CMAKE_ARGS -GNinja -DCMAKE_BUILD_TYPE=Release"
cmake $CMAKE_ARGS  -DCMAKE_CXX_STANDARD=17 .
cmake --build .
./flags_example
grep -q SHELL $PREFIX/lib/pkgconfig/absl_random_internal_randen_hwaes.pc && exit 1 || exit 0
exit 0
