mkdir build
pushd build

cmake %CMAKE_ARGS% -GNinja -D CMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% -D CMAKE_BUILD_TYPE=Release ..
if errorlevel 1 exit 1

ninja
if errorlevel 1 exit 1

:: Test.
if not "%CONDA_BUILD_SKIP_TESTS%"=="1" (
  ctest -C Release
)
if errorlevel 1 exit 1
