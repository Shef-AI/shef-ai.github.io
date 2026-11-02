

set -ex



pip check
pytest -k 'not (test_failures or test_failure_after_loading_additional_anchors or test_success_with_inject or test_minimum_maximum_version or test_check_hostname_false or test_sslcontext_api_failures_async)' tests/
exit 0
