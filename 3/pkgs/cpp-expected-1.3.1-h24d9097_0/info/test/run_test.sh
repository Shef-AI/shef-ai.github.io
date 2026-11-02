

set -ex



test -f ${PREFIX}/include/tl/expected.hpp
test -f ${PREFIX}/share/cmake/tl-expected/tl-expected-config.cmake
test -f ${PREFIX}/share/cmake/tl-expected/tl-expected-config-version.cmake
exit 0
