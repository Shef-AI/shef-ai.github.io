

set -ex



test ! -f ${PREFIX}/lib/libjansson.a
test -f ${PREFIX}/lib/libjansson${SHLIB_EXT}
exit 0
