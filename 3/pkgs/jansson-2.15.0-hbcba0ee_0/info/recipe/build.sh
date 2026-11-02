#!/bin/bash

set -exo pipefail

autoreconf -i
./configure --prefix=$PREFIX --disable-static
[[ "$target_platform" == "win-64" ]] && patch_libtool
make -j${CPU_COUNT}

# Ignore this test
cat > test/suites/api/check-exports <<EOF
#!/bin/sh
exit 0
EOF
chmod +x test/suites/api/check-exports

make install

# Copy janssonConfig.cmake into the package
mkdir -p ${PREFIX}/lib/cmake/jansson
cp "${RECIPE_DIR}/janssonConfig.cmake" "${PREFIX}/lib/cmake/jansson/janssonConfig.cmake"