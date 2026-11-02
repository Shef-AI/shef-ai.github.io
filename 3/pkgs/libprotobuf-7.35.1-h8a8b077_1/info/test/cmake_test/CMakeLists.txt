project(cf_dummy LANGUAGES C CXX)
cmake_minimum_required(VERSION 3.12)

# We need to specify CONFIG to make sure that CMake
# uses protobuf-config.cmake instead of relying on its
# own FindProtobuf.cmake that does not know about
# abseil transitive depedendency and about C++ version
# required, see https://github.com/conda-forge/conda-forge-pinning-feedstock/issues/4075#issuecomment-1569242816
find_package(Protobuf CONFIG REQUIRED)

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/struct_example.cc
"

#include <iostream>

#include <google/protobuf/struct.pb.h>

int main()
{
    google::protobuf::Struct myStruct;
}

"
)

add_executable(struct_example ${CMAKE_CURRENT_BINARY_DIR}/struct_example.cc)
target_link_libraries(struct_example PRIVATE protobuf::libprotobuf)
