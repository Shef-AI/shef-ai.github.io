cmake -B build/ ^
    -G "Ninja" ^
    -D SIMDJSON_DEVELOPER_MODE=OFF ^
    -D SIMDJSON_BUILD_STATIC_LIB=ON ^
    -D BUILD_SHARED_LIBS=ON ^
    -D CMAKE_BUILD_TYPE=Release ^
    -D CMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    %CMAKE_ARGS%
if errorlevel 1 exit 1

cmake --build build/ --parallel %CPU_COUNT% --verbose
if errorlevel 1 exit 1

cmake --install build/
if errorlevel 1 exit 1
