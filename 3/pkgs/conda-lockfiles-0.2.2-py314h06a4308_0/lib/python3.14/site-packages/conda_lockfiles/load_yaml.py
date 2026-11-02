from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from conda.common.serialize import yaml

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@cache
def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return yaml.load(fh)
