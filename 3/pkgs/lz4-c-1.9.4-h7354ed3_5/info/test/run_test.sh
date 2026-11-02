

set -ex



lz4 -h
lz4c -h
lz4cat -h
unlz4 -h
test -f ${PREFIX}/include/lz4.h
test -f ${PREFIX}/include/lz4hc.h
test -f ${PREFIX}/include/lz4frame.h
test ! -f ${PREFIX}/lib/liblz4.a
test -f ${PREFIX}/lib/liblz4.so
test -f ${PREFIX}/lib/pkgconfig/liblz4.pc
pkg-config --cflags --libs liblz4
exit 0
