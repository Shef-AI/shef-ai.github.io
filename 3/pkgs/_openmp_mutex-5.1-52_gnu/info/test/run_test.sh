

set -ex



echo "gnu mutex selected"
test ! -e "${PREFIX}/lib/libgomp.so.1"
exit 0
