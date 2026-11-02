

set -ex



set -x
test -f $PREFIX/lib/libkrb5${SHLIB_EXT}
test -f $PREFIX/include/krb5.h
test -f $PREFIX/include/gssapi.h
test -f $PREFIX/include/gssapi/gssapi.h
test -f $PREFIX/include/krb5/krb5.h
test -f $PREFIX/bin/krb5-config
exit 0
