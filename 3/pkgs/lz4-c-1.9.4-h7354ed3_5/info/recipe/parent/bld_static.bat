@echo off
:: Copy the static library built during the main build phase
COPY "%SRC_DIR%\build_static\lz4.lib" "%LIBRARY_LIB%\liblz4_static.lib"
if errorlevel 1 exit 1
