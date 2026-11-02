

set -ex



pip check
pytest -v tests  --ignore=tests/test_configurator.py --ignore=tests/metrics/exponential_histogram/test_exponent_mapping.py --ignore=tests/metrics/exponential_histogram/test_exponential_bucket_histogram_aggregation.py --ignore=tests/metrics/integration_test/test_console_exporter.py --ignore=tests/metrics/integration_test/test_exporter_concurrency.py --ignore=tests/metrics/test_backward_compat.py --ignore=tests/metrics/test_import.py --ignore=tests/metrics/test_metric_reader_storage.py --ignore=tests/metrics/test_metrics.py --ignore=tests/metrics/test_periodic_exporting_metric_reader.py --ignore=tests/trace/test_trace.py  --deselect=tests/context/test_asyncio.py::TestAsyncio::test_with_asyncio
exit 0
