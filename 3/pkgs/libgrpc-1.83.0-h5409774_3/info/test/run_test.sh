

set -ex



test -f $PREFIX/lib/libgpr$SHLIB_EXT
test -f $PREFIX/lib/libgrpc$SHLIB_EXT
test -f $PREFIX/lib/libgrpc++$SHLIB_EXT
test -f $PREFIX/lib/libaddress_sorting$SHLIB_EXT
test ! -f $PREFIX/lib/libgrpc_unsecure$SHLIB_EXT
test ! -f $PREFIX/lib/libgrpc++_unsecure$SHLIB_EXT
test ! -f $PREFIX/lib/libgpr.a
test ! -f $PREFIX/lib/libgrpc.a
test ! -f $PREFIX/lib/libgrpc++.a
test ! -f $PREFIX/lib/libaddress_sorting.a
test -f $PREFIX/bin/grpc_cpp_plugin
test -f $PREFIX/bin/grpc_csharp_plugin
test -f $PREFIX/bin/grpc_node_plugin
test -f $PREFIX/bin/grpc_objective_c_plugin
test -f $PREFIX/bin/grpc_php_plugin
test -f $PREFIX/bin/grpc_python_plugin
test -f $PREFIX/bin/grpc_ruby_plugin
pkg-config --print-errors --exact-version "56.0.0" gpr
pkg-config --print-errors --exact-version "56.0.0" grpc
pkg-config --print-errors --exact-version "1.83.0" grpc++
./test_grpc.sh
cd cmake_test
cmake -GNinja -DCMAKE_CXX_STANDARD=17 $CMAKE_ARGS .
cmake --build .
exit 0
