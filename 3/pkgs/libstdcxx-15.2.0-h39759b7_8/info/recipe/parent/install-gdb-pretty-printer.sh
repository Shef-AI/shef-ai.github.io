set -e -x

# install gcc's gdbhooks ...
mkdir -p "$SP_DIR"/gcc
cp $SRC_DIR/gcc/gcc/gdbhooks.py "$SP_DIR"/gcc/.

# install libstdc++'s pretty printer support
cp -r $SRC_DIR/gcc/libstdc++-v3/python/libstdcxx "$SP_DIR"/.

exit 0
