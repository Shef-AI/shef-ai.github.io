

set -ex



test -d ${PREFIX}/include/nlohmann
test -f ${PREFIX}/include/nlohmann/json.hpp
test -f ${PREFIX}/include/nlohmann/json_fwd.hpp
test -f ${PREFIX}/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake
test -f ${PREFIX}/share/cmake/nlohmann_json/nlohmann_jsonConfigVersion.cmake
test -f ${PREFIX}/share/cmake/nlohmann_json/nlohmann_jsonTargets.cmake
exit 0
