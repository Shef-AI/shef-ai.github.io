

set -ex



python -c "from importlib.metadata import version; assert(version('conda-libmamba-solver')=='26.10.0')"
conda create --solver libmamba -n test --dry-run scipy
exit 0
