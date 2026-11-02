

set -ex



pip check
pytest -v opentelemetry-proto/tests
exit 0
