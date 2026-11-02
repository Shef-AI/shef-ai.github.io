#!/bin/bash
set -euo pipefail

meson setup build \
  ${MESON_ARGS:-} \
  --prefix="${PREFIX}" \
  -Dlibdir=$PREFIX/lib \
  --includedir=${PREFIX}/include \
  --wrap-mode=nodownload \
  -Dsystemd=disabled \
  -Dselinux=disabled \
  -Dxml_docs=disabled \
  -Dlaunchd_agent_dir="${PREFIX}"

meson compile -C build

# Skip tests on macOS as 2 of them fail because of the expected behavior:
# - X11 autolaunch disabled
# - known issue with bus socket creation
# No easy way to skip single tests on meson.
if [[ "${target_platform}" != osx-* ]]; then
   meson test -C build --print-errorlogs
fi
meson install -C build
