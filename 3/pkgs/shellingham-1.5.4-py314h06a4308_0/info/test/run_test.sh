

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('shellingham')=='1.5.4')"
pytest -v tests
exit 0
