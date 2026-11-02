

set -ex



pip check
pytest tests -vv -k " not test_set_key_permission_error and not test_set_key_unauthorized_file"
exit 0
