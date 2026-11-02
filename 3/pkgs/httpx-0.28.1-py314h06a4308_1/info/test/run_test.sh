

set -ex



pip check
httpx --help
pytest -vv tests -k "not ( test_socks_proxy_deprecated or test_socks_proxy)"
exit 0
