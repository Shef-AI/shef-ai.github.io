@echo on

:: Remove -GL from CXXFLAGS as this causes a fatal error
set "CFLAGS= -MD"
set "CXXFLAGS= -MD"

mkdir -p build
cd build

cmake -G Ninja ^
    -DBUILD_SHARED_LIBS=ON ^
      -DCMAKE_CXX_STANDARD=17 ^
      -DCMAKE_BUILD_TYPE=Release ^
      -DCMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
    -DRE2_BUILD_TESTING=OFF ^
    ..
if %ERRORLEVEL% neq 0 exit 1

cmake --build .
if %ERRORLEVEL% neq 0 exit 1

:: same test filter as upstream uses, see build.sh
ctest --output-on-failure -E "dfa|exhaustive|random"
if %ERRORLEVEL% neq 0 exit 1
