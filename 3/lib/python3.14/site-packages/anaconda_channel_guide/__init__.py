"""anaconda-channel-guide: a conda plug-in for Anaconda's main-x channel."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

#: Application name.
APP_NAME: Final = "anaconda-channel-guide"

try:
    # Auto-generated during hatchling build
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0+placeholder"

#: Application version.
APP_VERSION: Final = __version__
