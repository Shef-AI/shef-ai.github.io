

set -ex



nghttp -nv https://nghttp2.org
test ! -f ${PREFIX}/lib/libnghttp2.a
test -f ${PREFIX}/lib/libnghttp2${SHLIB_EXT}
exit 0
