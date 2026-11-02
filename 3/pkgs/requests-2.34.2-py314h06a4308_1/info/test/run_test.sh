

set -ex



pip check
python -m conda
conda create -v --dry-run -n requests-test numpy
pytest -v  \
  -k "not (test_use_proxy_from_environment or TestRequests or TestTimeout \
  or test_requests_are_updated_each_time or tests/test_requests.py::test_urllib3_retries \
  or tests/test_requests.py::test_urllib3_pool_connection_closed or TestPreparingURLs \
  or test_content_length_for_bytes_data or test_content_length_for_string_data_counts_bytes \
  or test_urllib3_retries or test_urllib3_pool_connection_closed or test_zipped_paths_extracted)"

exit 0
