# janssonConfig.cmake
include_guard(GLOBAL)

if(NOT TARGET jansson::jansson)
  find_package(PkgConfig REQUIRED QUIET)
  pkg_check_modules(JANSSON REQUIRED jansson)

  add_library(jansson::jansson INTERFACE IMPORTED)
  set_target_properties(jansson::jansson PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${JANSSON_INCLUDE_DIRS}"
    INTERFACE_LINK_LIBRARIES "${JANSSON_LIBRARIES}"
  )

  message(STATUS "janssonConfig.cmake shim by conda-forge: created imported target jansson::jansson "
                 "from pkg-config (${JANSSON_VERSION})")
else()
  message(STATUS "janssonConfig.cmake shim: using existing jansson::jansson target")
endif()

set(JANSSON_LIBRARIES "${JANSSON_LIBRARIES}")
set(JANSSON_INCLUDE_DIRS "${JANSSON_INCLUDE_DIRS}")
set(JANSSON_VERSION "${JANSSON_VERSION}")