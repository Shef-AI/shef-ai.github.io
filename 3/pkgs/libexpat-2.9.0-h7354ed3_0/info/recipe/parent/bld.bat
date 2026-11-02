:: Needed so we can find stdint.h from msinttypes.
set LIB=%LIBRARY_LIB%;%LIB%
set LIBPATH=%LIBRARY_LIB%;%LIBPATH%
set INCLUDE=%LIBRARY_INC%;%INCLUDE%

:: set cflags because NDEBUG is set in Release configuration, which errors out in test suite due to no assert
cmake -G "Ninja" ^
      -D CMAKE_INSTALL_PREFIX=%LIBRARY_PREFIX% ^
      -D CMAKE_C_FLAGS_RELEASE="%CFLAGS%" ^
      -D CMAKE_CXX_FLAGS_RELEASE="%CXXFLAGS%" ^
      -D CMAKE_BUILD_TYPE=Release ^
      -D EXPAT_BUILD_TOOLS=ON ^
      -D EXPAT_BUILD_PKGCONFIG=OFF ^
      -D EXPAT_BUILD_TESTS=ON ^
      -D EXPAT_BUILD_EXAMPLES=OFF ^
      -D EXPAT_BUILD_DOCS=OFF ^
      -D BUILD_SHARED_LIBS=ON ^
      -S %SRC_DIR% ^
      -B build

:: Build and install.
cmake --build build --config Release --parallel %CPU_COUNT% --target install
if errorlevel 1 exit 1

:: Test.
ctest -C Release --test-dir build
if errorlevel 1 exit 1

:: Workaround for package that got build with latet version that renamed these.
copy %LIBRARY_BIN%\\libexpat.dll %LIBRARY_BIN%\\expat.dll || exit 1
copy %LIBRARY_LIB%\\libexpat.lib %LIBRARY_LIB%\\expat.lib || exit 1
