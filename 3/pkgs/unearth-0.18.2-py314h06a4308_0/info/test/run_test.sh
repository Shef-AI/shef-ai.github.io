

set -ex



pip check
pytest -v tests  --deselect=tests/test_evaluator.py::test_evaluate_packages_matching_version
exit 0
