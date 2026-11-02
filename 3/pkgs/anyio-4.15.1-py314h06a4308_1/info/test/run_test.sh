

set -ex



pip check
pytest -v -m "not network"  --deselect=tests/test_lazyimport.py::test_sourceless_install tests -k "not (test_happy_eyeballs and (dualstack or ipv6)) and not (test_connection_refused and multi)"
exit 0
