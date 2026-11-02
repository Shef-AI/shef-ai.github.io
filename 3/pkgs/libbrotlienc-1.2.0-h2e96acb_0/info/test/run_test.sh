

set -ex



test ! -f ${PREFIX}/lib/libbrotlienc-static.a
test -f ${PREFIX}/lib/libbrotlienc${SHLIB_EXT}
exit 0
