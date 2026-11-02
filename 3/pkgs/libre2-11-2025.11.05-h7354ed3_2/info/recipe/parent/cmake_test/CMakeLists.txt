project(cf_dummy LANGUAGES CXX)
cmake_minimum_required(VERSION 3.12)
find_package(absl REQUIRED CONFIG)

add_executable(re2_example re2_example.cpp)
target_link_libraries(re2_example absl::flags absl::strings)
