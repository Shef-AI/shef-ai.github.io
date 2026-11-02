

set -ex



test -f $PREFIX/lib/libicudata.a
test -f $PREFIX/lib/libicui18n.a
test -f $PREFIX/lib/libicuio.a
test -f $PREFIX/lib/libicutest.a
test -f $PREFIX/lib/libicutu.a
test -f $PREFIX/lib/libicuuc.a
test -f $PREFIX/lib/libicudata.so.78.3
test -f $PREFIX/lib/libicudata.so.78
test -L $PREFIX/lib/libicudata.so
test -f $PREFIX/lib/libicui18n.so.78.3
test -f $PREFIX/lib/libicui18n.so.78
test -L $PREFIX/lib/libicui18n.so
test -f $PREFIX/lib/libicuio.so.78.3
test -f $PREFIX/lib/libicuio.so.78
test -L $PREFIX/lib/libicuio.so
test -f $PREFIX/lib/libicutest.so.78.3
test -f $PREFIX/lib/libicutest.so.78
test -L $PREFIX/lib/libicutest.so
test -f $PREFIX/lib/libicutu.so.78.3
test -f $PREFIX/lib/libicutu.so.78
test -L $PREFIX/lib/libicutu.so
test -f $PREFIX/lib/libicuuc.so.78.3
test -f $PREFIX/lib/libicuuc.so.78
test -L $PREFIX/lib/libicuuc.so
test -f $PREFIX/include/unicode/utypes.h
test -f $PREFIX/include/unicode/uvernum.h
test -f $PREFIX/include/unicode/ucnv.h
test -f $PREFIX/include/unicode/unistr.h
grep -q "U_ICU_VERSION_MAJOR_NUM 78" $PREFIX/include/unicode/uvernum.h
grep -q 'U_ICU_VERSION "78.3"' $PREFIX/include/unicode/uvernum.h
test -f $PREFIX/lib/pkgconfig/icu-uc.pc
test -f $PREFIX/lib/pkgconfig/icu-i18n.pc
test -f $PREFIX/lib/pkgconfig/icu-io.pc
test -d $PREFIX/lib/icu
test -f $PREFIX/lib/icu/78.3/pkgdata.inc
test -f $PREFIX/lib/icu/78.3/Makefile.inc
test "$(icu-config --version)" = "78.3"
test -n "$(icu-config --prefix)"
test -n "$(icu-config --cflags)"
test -n "$(icu-config --cxxflags)"
test -n "$(icu-config --cppflags)"
test -n "$(icu-config --ldflags)"
test -n "$(icu-config --ldflags-icuio)"
genbrk --help
gencfu --help
gencnval --help
gendict --help
icuexportdata --help
icuinfo --help
icu-config --help
icuinfo | grep -F "78.3"
genrb tests/de.txt
test -s de.res
makeconv -d . tests/gb-18030-2000.ucm
test -s gb-18030-2000.cnv
exit 0
