

set -ex



pip check
normalizer --help
pytest -v tests/
exit 0
