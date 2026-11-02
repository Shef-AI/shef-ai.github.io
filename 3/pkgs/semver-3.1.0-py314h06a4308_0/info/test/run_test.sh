

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('semver')=='3.1.0')"
pytest -vv tests
pysemver -h
exit 0
