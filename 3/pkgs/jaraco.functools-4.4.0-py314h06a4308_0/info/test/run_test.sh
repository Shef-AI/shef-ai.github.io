

set -ex



pip check
pytest -vv test_functools.py -k "not test_function_throttled"
exit 0
