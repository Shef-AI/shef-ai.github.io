#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "gRPC::address_sorting" for configuration "Release"
set_property(TARGET gRPC::address_sorting APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::address_sorting PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libaddress_sorting.so.56.0.0"
  IMPORTED_SONAME_RELEASE "libaddress_sorting.so.56"
  )

list(APPEND _cmake_import_check_targets gRPC::address_sorting )
list(APPEND _cmake_import_check_files_for_gRPC::address_sorting "${_IMPORT_PREFIX}/lib/libaddress_sorting.so.56.0.0" )

# Import target "gRPC::gpr" for configuration "Release"
set_property(TARGET gRPC::gpr APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::gpr PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgpr.so.56.0.0"
  IMPORTED_SONAME_RELEASE "libgpr.so.56"
  )

list(APPEND _cmake_import_check_targets gRPC::gpr )
list(APPEND _cmake_import_check_files_for_gRPC::gpr "${_IMPORT_PREFIX}/lib/libgpr.so.56.0.0" )

# Import target "gRPC::grpc" for configuration "Release"
set_property(TARGET gRPC::grpc APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc PROPERTIES
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "gRPC::address_sorting;c-ares::cares;re2::re2;absl::hash;absl::random_distributions;absl::statusor"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc.so.56.0.0"
  IMPORTED_SONAME_RELEASE "libgrpc.so.56"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc )
list(APPEND _cmake_import_check_files_for_gRPC::grpc "${_IMPORT_PREFIX}/lib/libgrpc.so.56.0.0" )

# Import target "gRPC::grpc++" for configuration "Release"
set_property(TARGET gRPC::grpc++ APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc++ PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc++.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc++.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc++ )
list(APPEND _cmake_import_check_files_for_gRPC::grpc++ "${_IMPORT_PREFIX}/lib/libgrpc++.so.1.83.0" )

# Import target "gRPC::grpc++_alts" for configuration "Release"
set_property(TARGET gRPC::grpc++_alts APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc++_alts PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc++_alts.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc++_alts.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc++_alts )
list(APPEND _cmake_import_check_files_for_gRPC::grpc++_alts "${_IMPORT_PREFIX}/lib/libgrpc++_alts.so.1.83.0" )

# Import target "gRPC::grpc++_error_details" for configuration "Release"
set_property(TARGET gRPC::grpc++_error_details APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc++_error_details PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc++_error_details.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc++_error_details.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc++_error_details )
list(APPEND _cmake_import_check_files_for_gRPC::grpc++_error_details "${_IMPORT_PREFIX}/lib/libgrpc++_error_details.so.1.83.0" )

# Import target "gRPC::grpc++_reflection" for configuration "Release"
set_property(TARGET gRPC::grpc++_reflection APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc++_reflection PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc++_reflection.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc++_reflection.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc++_reflection )
list(APPEND _cmake_import_check_files_for_gRPC::grpc++_reflection "${_IMPORT_PREFIX}/lib/libgrpc++_reflection.so.1.83.0" )

# Import target "gRPC::grpc_authorization_provider" for configuration "Release"
set_property(TARGET gRPC::grpc_authorization_provider APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc_authorization_provider PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc_authorization_provider.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc_authorization_provider.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc_authorization_provider )
list(APPEND _cmake_import_check_files_for_gRPC::grpc_authorization_provider "${_IMPORT_PREFIX}/lib/libgrpc_authorization_provider.so.1.83.0" )

# Import target "gRPC::grpc_plugin_support" for configuration "Release"
set_property(TARGET gRPC::grpc_plugin_support APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpc_plugin_support PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpc_plugin_support.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpc_plugin_support.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpc_plugin_support )
list(APPEND _cmake_import_check_files_for_gRPC::grpc_plugin_support "${_IMPORT_PREFIX}/lib/libgrpc_plugin_support.so.1.83.0" )

# Import target "gRPC::grpcpp_channelz" for configuration "Release"
set_property(TARGET gRPC::grpcpp_channelz APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(gRPC::grpcpp_channelz PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libgrpcpp_channelz.so.1.83.0"
  IMPORTED_SONAME_RELEASE "libgrpcpp_channelz.so.1.83"
  )

list(APPEND _cmake_import_check_targets gRPC::grpcpp_channelz )
list(APPEND _cmake_import_check_files_for_gRPC::grpcpp_channelz "${_IMPORT_PREFIX}/lib/libgrpcpp_channelz.so.1.83.0" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
