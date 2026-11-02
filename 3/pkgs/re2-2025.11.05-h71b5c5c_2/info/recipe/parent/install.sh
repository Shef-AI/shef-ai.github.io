#!/bin/bash
set -ex

if [[ "$PKG_NAME" == "re2" ]]; then
    # everything else but the versioned libs
    cmake --install ./build
else
    # package only the versioned library for the output libre2-{{soversion}};
    # sorted second because it keeps changing names, easier in "else"
    if [[ "${target_platform}" == linux-* ]]; then
        cp ./build/libre2.so.* $PREFIX/lib
    else
        cp ./build/libre2.*.dylib $PREFIX/lib
    fi
fi
