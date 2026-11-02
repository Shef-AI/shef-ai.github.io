@echo on

SetLocal EnableDelayedExpansion

mkdir build
cd build

if [%PKG_NAME%] == [libabseil-tests] (
    set "EXTRA_ARGS=-DBUILD_TESTING=ON -DABSL_BUILD_TEST_HELPERS=ON -DABSL_BUILD_TESTING=ON"
    set "EXTRA_ARGS=!EXTRA_ARGS! -DABSL_USE_EXTERNAL_GOOGLETEST=ON -DABSL_FIND_GOOGLETEST=ON"
)

cmake -GNinja ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_CXX_STANDARD=17 ^
    -DCMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    -DCMAKE_PREFIX_PATH=%LIBRARY_PREFIX% ^
    -DBUILD_SHARED_LIBS=ON ^
    -DABSL_PROPAGATE_CXX_STD=ON ^
    !EXTRA_ARGS! ^
    ..
if %ERRORLEVEL% neq 0 exit 1

cmake --build .
if %ERRORLEVEL% neq 0 exit 1

cmake --build . --target install
if %ERRORLEVEL% neq 0 exit 1
