

set -ex



abi3audit $SP_DIR/rattler/rattler.abi3.so -s -v --assume-minimum-abi3 3.10
pip check
exit 0
