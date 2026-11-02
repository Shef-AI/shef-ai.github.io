cmake_minimum_required(VERSION 3.20)

project(test-simdjson LANGUAGES CXX)

add_executable(test-simdjson test.cpp)

find_package(simdjson REQUIRED)
target_link_libraries(test-simdjson PRIVATE simdjson::${TEST_TARGET})

enable_testing()
add_test(NAME test-simdjson COMMAND test-simdjson "${CMAKE_CURRENT_SOURCE_DIR}/test.json")
