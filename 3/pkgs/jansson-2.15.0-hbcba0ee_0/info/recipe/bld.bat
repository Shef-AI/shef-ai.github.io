mkdir "%SRC_DIR%"\build
pushd "%SRC_DIR%"\build

cmake -G "Ninja" ^
      -DCMAKE_INSTALL_PREFIX="%LIBRARY_PREFIX%" ^
      -DCMAKE_BUILD_TYPE=Release ^
      -DJANSSON_BUILD_SHARED_LIBS=ON ^
      -DJANSSON_BUILD_DOCS=OFF ^
      -DJANSSON_EXAMPLES=OFF ^
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ^
      %CMAKE_ARGS% ^
      ..
if errorlevel 1 exit 1

cmake --build . --target install --config Release
if errorlevel 1 exit 1
