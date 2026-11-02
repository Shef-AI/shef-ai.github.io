

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('pycparser')=='3.11')"
pytest --rootdir=. -vv tests
exit 0
