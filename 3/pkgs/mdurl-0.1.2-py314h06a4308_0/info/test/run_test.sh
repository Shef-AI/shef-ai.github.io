

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('mdurl')=='0.1.2')"
pytest -v gh/tests
exit 0
