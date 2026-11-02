project(cf_dummy LANGUAGES C CXX)
cmake_minimum_required(VERSION 3.12)
find_package(gRPC REQUIRED)

add_executable(grpc_example ${CMAKE_CURRENT_BINARY_DIR}/grpc_example.cc)
target_link_libraries(grpc_example PRIVATE gRPC::grpc++)
