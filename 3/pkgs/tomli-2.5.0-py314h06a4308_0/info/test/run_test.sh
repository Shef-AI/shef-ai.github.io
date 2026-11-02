

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('tomli')=='2.5.0')"
pytest -vv tests
exit 0
