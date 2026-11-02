

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('markdown-it-py')=='4.2.0')"
pytest -k "not(test_commonmark_extras or test_table_tokens or test_file or test_use_existing_env or test_store_labels or test_inline_definitions or test_pretty or test_pretty_text_special)" -v gh/tests
markdown-it --help
exit 0
