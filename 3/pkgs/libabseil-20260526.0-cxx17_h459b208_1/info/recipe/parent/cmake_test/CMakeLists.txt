project(cf_dummy LANGUAGES CXX)
cmake_minimum_required(VERSION 3.12)
find_package(absl REQUIRED CONFIG)

add_executable(flags_example flags_example.cpp)
target_link_libraries(flags_example absl::flags absl::strings)

if(DEFINED ENV{TRY_TEST_TARGET})
    # check if we can find a test target (i.e. that the cmake metadata from
    # vanilla libabseil has been updated correctly for libabseil-tests)
    target_link_libraries(flags_example absl::scoped_mock_log)
endif()
