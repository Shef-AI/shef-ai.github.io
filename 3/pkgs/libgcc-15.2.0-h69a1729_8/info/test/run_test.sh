

set -ex



test -f ${PREFIX}/lib/libgcc_s.so
test ! -e ${PREFIX}/lib/libgomp.so.1.0.0
test ! -e ${PREFIX}/lib/libgomp.so.1
exit 0
