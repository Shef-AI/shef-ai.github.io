

set -ex



pip check
python -c "from pydantic_core import PydanticUndefinedType"
pytest -vv --ignore=tests/test_docstrings.py --ignore=tests/test_tzinfo.py --ignore=tests/validators/test_allow_partial.py -W default::pytest.PytestUnknownMarkWarning -W default::pytest.PytestRemovedIn10Warning
exit 0
