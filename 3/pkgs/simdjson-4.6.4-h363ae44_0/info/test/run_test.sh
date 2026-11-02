

set -ex



test -f "${PREFIX}/include/simdjson.h"
test -f "${PREFIX}/lib/libsimdjson${SHLIB_EXT}"
test -f "${PREFIX}/lib/cmake/simdjson/simdjson-config.cmake"
cmake -G Ninja -S test/ -B build/ -D TEST_TARGET=simdjson ${CMAKE_ARGS}
cmake --build build/
cmake --build build --target test
exit 0
