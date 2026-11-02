

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('readchar')=='4.2.2')"
pytest -s -v tests/linux
exit 0
