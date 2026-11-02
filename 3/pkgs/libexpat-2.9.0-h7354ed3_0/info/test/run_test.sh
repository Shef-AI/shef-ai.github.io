

set -ex



ls $PREFIX/lib/libexpat*${SHLIB_EXT}* > /dev/null 2>&1
pkg-config --libs expat
exit 0
