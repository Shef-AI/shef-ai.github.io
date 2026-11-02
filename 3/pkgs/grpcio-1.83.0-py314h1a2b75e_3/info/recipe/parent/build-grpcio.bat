if "%ARCH%" == "32" (set PLATFORM=x86) else (set PLATFORM=x64)

set "GRPC_BUILD_WITH_BORING_SSL_ASM="
set "GRPC_PYTHON_BUILD_SYSTEM_ABSL=True"
set "GRPC_PYTHON_BUILD_SYSTEM_CARES=True"
set "GRPC_PYTHON_BUILD_SYSTEM_GRPC_CORE=True"
set "GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=True"
set "GRPC_PYTHON_BUILD_SYSTEM_RE2=True"
set "GRPC_PYTHON_BUILD_SYSTEM_ZLIB=True"
set "GRPC_PYTHON_BUILD_WITH_CYTHON=True"
set "GRPC_PYTHON_CFLAGS=/DPB_FIELD_16BIT /std:c++17"

:: clearing this regenerates it with cython and fixes phtread usage
del src\python\grpcio\grpc\_cython\cygrpc.cpp

"%PYTHON%" -m pip install . --no-deps --no-build-isolation --ignore-installed --no-cache-dir -v
if %ERRORLEVEL% neq 0 exit 1
