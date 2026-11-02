#!/bin/bash

export GRPC_PYTHON_BUILD_WITH_CYTHON=true 
cd tools/distrib/python/grpcio_tools
${PYTHON} -m pip install --no-deps --no-build-isolation . -vv

