
mkdir build
cd build

cmake -D CMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
-D CMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
-D CMAKE_BUILD_TYPE=Release ^
-D LIBXML2_WITH_ICU=no ^
-D LIBXML2_WITH_SCHEMATRON=yes ^
-D LIBXML2_WITH_PYTHON=no ^
-G "NMake Makefiles" ..

if errorlevel 1 exit 1

nmake
if errorlevel 1 exit 1

nmake install
if errorlevel 1 exit 1

del %LIBRARY_PREFIX%\bin\test*.exe || exit 1
del %LIBRARY_PREFIX%\bin\runsuite.exe || exit 1
del %LIBRARY_PREFIX%\bin\runtest.exe || exit 1
