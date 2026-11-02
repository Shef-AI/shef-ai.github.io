"""
conda self: manage your base conda installation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

#: Application name.
APP_NAME: Final = "conda-self"

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0+placeholder"

#: Application version.
APP_VERSION: Final = __version__
