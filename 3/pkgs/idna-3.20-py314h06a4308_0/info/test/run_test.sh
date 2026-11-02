

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('idna')=='3.20')"
idna --help
pytest -v tests
exit 0
