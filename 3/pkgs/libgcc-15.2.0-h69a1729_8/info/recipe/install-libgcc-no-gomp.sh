#!/bin/bash

source ${RECIPE_DIR}/setup_compiler.sh
set -e -x

export CHOST="${triplet}"

# we have to remove existing links/files so that the libgcc install works
rm -rf ${PREFIX}/lib/*
rm -rf ${PREFIX}/share/*
rm -f ${PREFIX}/${CHOST}/lib/libgomp*

# now run install of libgcc
# this reinstalls the wrong symlinks for openmp
source ${RECIPE_DIR}/install-libgcc.sh

# remove and relink things for openmp
rm -f ${PREFIX}/lib/libgomp.so
rm -f ${PREFIX}/${CHOST}/lib/libgomp.so
rm -f ${PREFIX}/lib/libgomp.so.${libgomp_ver:0:1}
rm -f ${PREFIX}/${CHOST}/lib/libgomp.so.${libgomp_ver:0:1}
rm -f ${PREFIX}/lib/libgomp.so.${libgomp_ver}
rm -f ${PREFIX}/${CHOST}/lib/libgomp.so.${libgomp_ver}
