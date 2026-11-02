

set -ex



touch checksum.txt
openssl sha256 checksum.txt
openssl ecparam -name prime256v1
python -c "import urllib.request; urllib.request.urlopen('https://pypi.org')"
pkg-config --print-errors --exact-version "3.5.9" openssl
test -f ${PREFIX}/lib/libcrypto.so.3
test -f ${PREFIX}/lib/libssl.so.3
test -f ${PREFIX}/lib/pkgconfig/libssl.pc
test -f ${PREFIX}/lib/pkgconfig/libcrypto.pc
test -f ${PREFIX}/lib/pkgconfig/openssl.pc
test -f ${PREFIX}/bin/openssl
test -f ${PREFIX}/bin/c_rehash
test -n "$(ls -A ${PREFIX}/include/openssl 2>/dev/null)"
exit 0
