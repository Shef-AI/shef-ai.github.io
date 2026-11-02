"""
conda index. Create repodata.json for collections of conda packages.
"""

try:
    from ._version import __version__
except ImportError:
    # _version.py is only created after running `pip install`
    try:
        from setuptools_scm import get_version

        __version__ = get_version(root="..", relative_to=__file__)
    except (ImportError, OSError, LookupError):
        # ImportError: setuptools_scm isn't installed
        # OSError: git isn't installed
        # LookupError: setuptools_scm unable to detect version
        # Conda abides by CEP-8 which specifies using CalVer, so the dev version is:
        #     YY.MM.MICRO.devN+gHASH[.dirty]
        __version__ = "0.0.0.dev0+placeholder"
