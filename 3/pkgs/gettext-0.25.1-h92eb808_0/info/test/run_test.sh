

set -ex



test -f ${PREFIX}/lib/libgettextlib$SHLIB_EXT
test ! -f ${PREFIX}/lib/libgettextlib.a
test -f ${PREFIX}/lib/libgettextpo$SHLIB_EXT
test ! -f ${PREFIX}/lib/libgettextpo.a
test -f ${PREFIX}/lib/libgettextsrc$SHLIB_EXT
test ! -f ${PREFIX}/lib/libgettextsrc.a
exit 0
