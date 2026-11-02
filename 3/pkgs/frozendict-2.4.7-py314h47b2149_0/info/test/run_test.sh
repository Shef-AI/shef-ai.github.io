

set -ex



pip check
pytest -v test  --deselect=test/test_frozendict_subclass.py::TestFrozendictSubclass::test_copycopy_sub
exit 0
