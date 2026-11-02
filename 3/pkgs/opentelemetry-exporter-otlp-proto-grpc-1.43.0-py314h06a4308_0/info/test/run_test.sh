

set -ex



pip check
pytest -v tests  --ignore=tests/test_otlp_metrics_exporter.py --ignore=tests/test_otlp_trace_exporter.py --ignore=tests/test_otlp_exporter_mixin.py
exit 0
