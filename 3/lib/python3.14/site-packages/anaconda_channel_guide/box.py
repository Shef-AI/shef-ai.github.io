from __future__ import annotations

import math
import shutil
from typing import TYPE_CHECKING

from conda.models.match_spec import MatchSpec

# Cap rendered box width so it stays readable on wide terminals.
MAX_WIDTH = 84

LOGIN_STEP = "Log in:\n    $ anaconda login"
CONFIG_STEP = (
    "Add the 'main-x' channel:\n"
    "    $ conda config --append default_channels https://repo.anaconda.cloud/repo/main-x"
)
DISABLE_STEP = (
    "To disable these notifications, please run:\n"
    "    $ conda config --set plugins.anaconda_channel_guide false"
)
TOS_MESSAGE = (
    "By accessing main-x, you agree to Anaconda's Terms of Service:\n"
    "    https://www.anaconda.com/legal/terms/terms-of-service"
)


if TYPE_CHECKING:
    from collections.abc import Iterable


class ChannelGuideBox:
    """Plain-text channel guide message for PNFE remediation."""

    TITLE = "Anaconda Channel Guide"
    MARGIN = 5  # Left margin for the box's content, in spaces.

    def __init__(self, packages: Iterable[str | MatchSpec], steps: list[str]) -> None:
        """
        :param packages: Packages that triggered the PNFE
        :param steps: Numbered action items for the user
        """
        self.packages = packages
        self.steps = steps

    def _intro_line(self) -> str:
        names = [pkg.name if isinstance(pkg, MatchSpec) else pkg for pkg in self.packages]
        if len(names) == 1:
            preamble = f"'{names[0]}' is"
        elif len(names) == 2:
            preamble = f"'{names[0]}' and '{names[1]}' are"
        else:
            *rest, last = names
            joined = ", ".join(f"'{n}'" for n in rest)
            preamble = f"{joined}, and '{last}' are"
        return f"{preamble} available in Anaconda's 'main-x' channel."

    @staticmethod
    def _render_block(block: str, prefix: str = "", indent: int = MARGIN) -> list[str]:
        title, *command_lines = block.splitlines()
        indent_str = " " * indent
        return [f"{prefix}{title}", *(f"{indent_str}{c.strip()}" for c in command_lines)]

    def plain_text_message(self) -> str:
        width = self._width() or MAX_WIDTH
        steps = [*self.steps, "Re-run the original command."]
        margin = " " * self.MARGIN

        title = f" {self.TITLE} "
        min_title_width = len(title) + 2
        title_width = width

        if title_width < min_title_width:
            ceiling = math.ceil(min_title_width / width)
            title_width = width * ceiling

        parts = [title.center(title_width, "-"), self._intro_line()]
        for i, step in enumerate(steps, 1):
            parts += self._render_block(step, prefix=f"{margin}{i}. ", indent=self.MARGIN * 2)
        parts.append("-" * width)
        for block in (TOS_MESSAGE, DISABLE_STEP):
            parts += self._render_block(block)

        return "\n\n" + "\n\n".join(parts)

    @staticmethod
    def _width() -> int:
        """Fit the real terminal width, capped at MAX_WIDTH so it stays readable."""
        return min(shutil.get_terminal_size(fallback=(MAX_WIDTH, 0)).columns, MAX_WIDTH)
