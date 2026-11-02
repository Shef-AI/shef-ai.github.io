cmake ^
	-G "Ninja" ^
	-D CMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
	-D JSON_BuildTests=OFF ^
	%SRC_DIR%

if errorlevel 1 exit 1

ninja
if errorlevel 1 exit 1

ninja install
if errorlevel 1 exit 1
