

set -ex



pip check
pytest tests -v  --deselect=tests/test_fuzzing.py::TestFuzzing::test_cma_tell --deselect=tests/test_core_tags.py::TestIfCondition::test_elif_deep
exit 0
