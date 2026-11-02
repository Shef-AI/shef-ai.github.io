meson setup builddir ^
    --prefix=%LIBRARY_PREFIX% ^
    --libdir=lib ^
    -Dbuildtype=release ^
    -Dlegacy=true
if errorlevel 1 exit 1

ninja -C builddir
if errorlevel 1 exit 1

ninja install -C builddir
if errorlevel 1 exit 1

meson test -C builddir --print-errorlogs
if errorlevel 1 exit 1
