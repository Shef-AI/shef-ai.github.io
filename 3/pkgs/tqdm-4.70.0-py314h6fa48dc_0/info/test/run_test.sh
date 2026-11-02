

set -ex



pip check
tqdm --help
tqdm -v | rg 4.70.0
pytest -vv -k "not (test_pandas_leave or tests_perf)" tests/ -W ignore::FutureWarning
exit 0
