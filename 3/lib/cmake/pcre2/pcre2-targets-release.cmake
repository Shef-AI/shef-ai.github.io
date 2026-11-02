#----------------------------------------------------------------
# Generated CMake target import file for configuration "release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "pcre2::pcre2-8-static" for configuration "release"
set_property(TARGET pcre2::pcre2-8-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-8-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-8.a"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-8-static )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-8-static "${_IMPORT_PREFIX}/lib/libpcre2-8.a" )

# Import target "pcre2::pcre2-posix-static" for configuration "release"
set_property(TARGET pcre2::pcre2-posix-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-posix-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-posix.a"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-posix-static )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-posix-static "${_IMPORT_PREFIX}/lib/libpcre2-posix.a" )

# Import target "pcre2::pcre2-8-shared" for configuration "release"
set_property(TARGET pcre2::pcre2-8-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-8-shared PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-8.so.0.16.1"
  IMPORTED_SONAME_RELEASE "libpcre2-8.so.0"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-8-shared )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-8-shared "${_IMPORT_PREFIX}/lib/libpcre2-8.so.0.16.1" )

# Import target "pcre2::pcre2-posix-shared" for configuration "release"
set_property(TARGET pcre2::pcre2-posix-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-posix-shared PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-posix.so.3.0.9"
  IMPORTED_SONAME_RELEASE "libpcre2-posix.so.3"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-posix-shared )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-posix-shared "${_IMPORT_PREFIX}/lib/libpcre2-posix.so.3.0.9" )

# Import target "pcre2::pcre2-16-static" for configuration "release"
set_property(TARGET pcre2::pcre2-16-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-16-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-16.a"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-16-static )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-16-static "${_IMPORT_PREFIX}/lib/libpcre2-16.a" )

# Import target "pcre2::pcre2-16-shared" for configuration "release"
set_property(TARGET pcre2::pcre2-16-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-16-shared PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-16.so.0.16.1"
  IMPORTED_SONAME_RELEASE "libpcre2-16.so.0"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-16-shared )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-16-shared "${_IMPORT_PREFIX}/lib/libpcre2-16.so.0.16.1" )

# Import target "pcre2::pcre2-32-static" for configuration "release"
set_property(TARGET pcre2::pcre2-32-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-32-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-32.a"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-32-static )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-32-static "${_IMPORT_PREFIX}/lib/libpcre2-32.a" )

# Import target "pcre2::pcre2-32-shared" for configuration "release"
set_property(TARGET pcre2::pcre2-32-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2-32-shared PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libpcre2-32.so.0.16.1"
  IMPORTED_SONAME_RELEASE "libpcre2-32.so.0"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2-32-shared )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2-32-shared "${_IMPORT_PREFIX}/lib/libpcre2-32.so.0.16.1" )

# Import target "pcre2::pcre2grep" for configuration "release"
set_property(TARGET pcre2::pcre2grep APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2grep PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/pcre2grep"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2grep )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2grep "${_IMPORT_PREFIX}/bin/pcre2grep" )

# Import target "pcre2::pcre2test" for configuration "release"
set_property(TARGET pcre2::pcre2test APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(pcre2::pcre2test PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/pcre2test"
  )

list(APPEND _cmake_import_check_targets pcre2::pcre2test )
list(APPEND _cmake_import_check_files_for_pcre2::pcre2test "${_IMPORT_PREFIX}/bin/pcre2test" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
