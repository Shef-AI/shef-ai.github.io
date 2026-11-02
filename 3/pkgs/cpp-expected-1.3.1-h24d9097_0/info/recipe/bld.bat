:: cmd

:: Isolate the build.
mkdir Build
cd Build
if errorlevel 1 exit 1

:: Generate the build files.
cmake .. -G"Ninja" %CMAKE_ARGS% ^
    -DCMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
    -DCMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    -DCMAKE_BUILD_TYPE=Release

:: Build.
ninja
if errorlevel 1 exit 1

:: Run tests.
.\tl-expected-tests
if errorlevel 1 exit 1

:: Install.
ninja install
if errorlevel 1 exit 1
