

set -ex



test ! -f $PREFIX/lib/libbrotlidec-static.a
test -f $PREFIX/lib/libbrotlidec$SHLIB_EXT
exit 0
