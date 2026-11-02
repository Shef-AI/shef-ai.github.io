#!/bin/bash

make install

if [[ "$PKG_NAME" == *static ]]
then
    rm -rfv ${PREFIX}/bin/*
    rm -rfv ${PREFIX}/lib/*.so* ${PREFIX}/lib/*.dylib
else
    rm -rfv ${PREFIX}/lib/*.a
fi
