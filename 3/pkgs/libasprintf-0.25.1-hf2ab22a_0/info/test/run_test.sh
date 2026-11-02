

set -ex



test -f ${PREFIX}/lib/libasprintf.so.0
test ! -f ${PREFIX}/lib/libasprintf$SHLIB_EXT
exit 0
