

set -ex



pip check
python -c "from importlib.metadata import version; assert(version('brotlicffi')=='1.2.0.1')"
exit 0
