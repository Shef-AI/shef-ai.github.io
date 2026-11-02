

set -ex



test ! -f ${PREFIX}/lib/libbrotlicommon-static.a
test -f ${PREFIX}/lib/libbrotlicommon${SHLIB_EXT}
exit 0
