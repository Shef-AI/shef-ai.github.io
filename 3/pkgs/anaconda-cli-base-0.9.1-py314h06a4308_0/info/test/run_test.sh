

set -ex



pip check
anaconda -h
anaconda -V
python -c "from anaconda_cli_base import __version__; assert __version__ == \"0.9.1\""
python -c "from importlib.metadata import version; assert(version('anaconda-cli-base')=='0.9.1')"
pytest -v tests --ignore=tests/test_telemetry_integration.py
exit 0
