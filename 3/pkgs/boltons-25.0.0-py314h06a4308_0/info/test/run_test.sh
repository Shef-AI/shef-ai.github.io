

set -ex



echo [pytest] > pytest.ini
echo doctest_optionflags = NORMALIZE_WHITESPACE IGNORE_EXCEPTION_DETAIL ELLIPSIS ALLOW_UNICODE >> pytest.ini
pytest -vv --doctest-modules boltons tests
pip check
exit 0
