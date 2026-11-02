

set -ex



test -f ${PREFIX}/lib/libprotoc.so
test ! -f ${PREFIX}/lib/libprotoc.a
test -f ${PREFIX}/lib/libprotobuf.so
test ! -f ${PREFIX}/lib/libprotobuf.a
test -f ${PREFIX}/lib/libprotobuf-lite.so
test ! -f ${PREFIX}/lib/libprotobuf-lite.a
test -f ${PREFIX}/lib/libutf8_range.so
test ! -f ${PREFIX}/lib/libutf8_range.a
test -f ${PREFIX}/lib/libutf8_validity.so
test ! -f ${PREFIX}/lib/libutf8_validity.a
test -d ${PREFIX}/include/upb
test -f ${PREFIX}/lib/libupb.a
test -f ${PREFIX}/include/upb/wire/internal/reader.h
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] upb_Arena_Free"
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] upb_Arena_Init"
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] upb_Decode"
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] upb_Encode"
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] upb_alloc_global"
nm -g $PREFIX/lib/libupb.a | grep -E "[TD] _upb_Arena_SlowMalloc_dont_copy_me__upb_internal_use_only"
test -f ${PREFIX}/lib/cmake/protobuf/protobuf-config.cmake
pkg-config --print-errors --exact-version "35.1.0" protobuf
pkg-config --print-errors --exact-version "35.1.0" protobuf-lite
protoc --help
cd cmake_test
cmake -GNinja $CMAKE_ARGS .
cmake --build .
exit 0
