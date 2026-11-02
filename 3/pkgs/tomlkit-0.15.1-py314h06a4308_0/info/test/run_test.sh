

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('tomlkit')=='0.15.1')"
pytest -ra -v --tb=short tests
exit 0
