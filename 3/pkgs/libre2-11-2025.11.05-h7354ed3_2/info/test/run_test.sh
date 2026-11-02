

set -ex



test -f ${PREFIX}/lib/libre2.so.11
test ! -f ${PREFIX}/lib/libre2.so
exit 0
