

set -ex



pip check
python -c "from anaconda_channel_guide import __version__; assert __version__ == \"0.2.0\""
python -c "from importlib.metadata import version; assert version('anaconda-channel-guide') == '0.2.0'"
pytest -v tests
exit 0
