#!/bin/bash

set -exuo pipefail

# rsync -a --prune-empty-dirs --include '*/' --include '*.h' --exclude '*' python/ $PREFIX/include/
cd python/
find . -type d -exec mkdir -p $PREFIX/include/{} \;
find . -type f -name '*.h' -exec cp {} $PREFIX/include/{} \;
find $PREFIX/include/ -type d -empty -delete