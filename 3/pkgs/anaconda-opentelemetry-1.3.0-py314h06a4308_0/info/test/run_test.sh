

set -ex



pip check
export OTEL_USE_CONSOLE_EXPORTER=TRUE
python -m pytest ./tests/unit_tests/ -k "not (test_export_errors_print or test_export_errors_silenced)"
exit 0
