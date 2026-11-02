@echo on

@rem Compile a trivial service definition to C++
protoc -I. --plugin=protoc-gen-grpc=%LIBRARY_PREFIX%/bin/grpc_cpp_plugin.exe --grpc_out=. hello.proto || exit /B
if %ERRORLEVEL% neq 0 exit 1

if not exist hello.grpc.pb.h exit 1
if not exist hello.grpc.pb.cc exit 1

:: taken from cd examples/cpp/helloworld
cd examples/cpp/helloworld

:: folder already contains a file called BUILD
mkdir build-cpp
cd build-cpp

:: CMake does not like paths with \ characters
set LIBRARY_PREFIX="%LIBRARY_PREFIX:\=/%"

cmake -G "Ninja" ^
    -DCMAKE_CXX_STANDARD=17 ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_PREFIX_PATH="%LIBRARY_PREFIX%" ^
    -DCMAKE_MODULE_PATH="%LIBRARY_PREFIX%/lib/cmake" ^
    ..
if %ERRORLEVEL% neq 0 exit 1

cmake --build . --config Release
if %ERRORLEVEL% neq 0 exit 1
