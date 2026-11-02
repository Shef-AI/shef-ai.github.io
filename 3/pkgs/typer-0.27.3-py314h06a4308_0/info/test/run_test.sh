

set -ex



pip check
typer --version
typer --help
PYTHONPATH=. coverage run --source=typer --branch -m pytest tests -vv --color=yes --tb=long -k "not ((multiple_values and main) or completion or invalid_score or test_file_error)"  --deselect=tests/test_tracebacks.py::test_rich_exceptions_dont_truncate_code_on_wide_terminal --deselect=tests/test_tutorial/test_printing/test_tutorial001.py::test_cli --deselect=tests/test_tutorial/test_printing/test_tutorial002.py::test_cli
exit 0
