from __future__ import annotations

import subprocess
import sys

from anaconda_channel_guide.plugin import MAIN_X_CHANNEL_URL, is_main_x_channel


def prefetch_main_x_repodata(_command: str) -> None:
    """Temporarily work around unsharded main/main-x repodata with a cache fill."""
    try:
        from conda.base.context import context

        has_main_x = any(is_main_x_channel(channel) for channel in (context.channels or ()))
        if context.offline or has_main_x:
            return

        subdirs = (context.subdir, "noarch") if context.subdir else ("noarch",)
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "anaconda_channel_guide.prefetch",
                *subdirs,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception:
        return


def main(argv: list[str] | None = None) -> int:
    subdirs = tuple(sys.argv[1:] if argv is None else argv) or ("noarch",)
    try:
        from conda.base.context import context, reset_context
        from conda.core.subdir_data import SubdirData
        from conda.models.channel import Channel, all_channel_urls

        reset_context()
        if not context.offline:
            for url in all_channel_urls([MAIN_X_CHANNEL_URL], subdirs=subdirs):
                SubdirData(Channel(url)).load()
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
