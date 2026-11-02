# Module path
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/modules)

# Depend packages
if(NOT ZLIB_FOUND)
  find_package(ZLIB)
endif()
include(CMakeFindDependencyMacro)
find_dependency(Protobuf CONFIG)
if(NOT OPENSSL_FOUND)
  find_package(OpenSSL)
endif()
if(NOT c-ares_FOUND)
  find_package(c-ares)
endif()
if(NOT TARGET absl::strings)
  find_package(absl CONFIG)
endif()
if(NOT re2_FOUND)
  find_package(re2)
endif()


# Targets
include(${CMAKE_CURRENT_LIST_DIR}/gRPCTargets.cmake)
if(NOT CMAKE_CROSSCOMPILING)
  include(${CMAKE_CURRENT_LIST_DIR}/gRPCPluginTargets.cmake)
endif()
