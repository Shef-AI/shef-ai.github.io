

set -ex



test -f ${PREFIX}/lib/libgettextpo.so.0
test ! -f ${PREFIX}/lib/libgettextpo$SHLIB_EXT
exit 0
