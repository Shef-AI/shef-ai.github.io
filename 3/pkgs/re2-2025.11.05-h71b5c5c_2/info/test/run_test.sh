

set -ex



test -f ${PREFIX}/lib/libre2.so
test ! -f ${PREFIX}/lib/libre2.a
test -f ${PREFIX}/include/re2/re2.h
pkg-config --print-errors --exact-version "11.0.0" re2
cd cmake_test
cmake -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 .
cmake --build .
./re2_example
exit 0
