

set -ex



pip check
py.test -v tests
keyring --help
exit 0
