

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('pydantic')=='2.14.1')"
pytest -ra -vv --tb=short tests  --ignore=tests/test_docs.py  --deselect=tests/test_types_typeddict.py::test_readonly_qualifier_warning --deselect=tests/test_deprecated_fields.py::test_deprecated_fields --deselect=tests/test_deprecated_fields.py::test_deprecated_fields_deprecated_class --deselect=tests/test_deprecated_fields.py::test_computed_field_deprecated --deselect=tests/test_deprecated_fields.py::test_deprecated_with_boolean --deselect=tests/test_deprecated_fields.py::test_deprecated_field_forward_annotation
exit 0
