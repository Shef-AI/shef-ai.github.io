

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('more-itertools')=='11.1.0')"
pytest -vv tests
exit 0
