

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('certifi')=='2026.10.19')"
pytest -vv certifi/certifi/tests
exit 0
