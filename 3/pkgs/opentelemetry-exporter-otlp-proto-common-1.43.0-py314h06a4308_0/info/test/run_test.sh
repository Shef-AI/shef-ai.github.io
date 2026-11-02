

set -ex



pip check
pytest -v tests  --ignore=tests/test_metrics_encoder.py
exit 0
