#!/bin/sh
set -e
mkdir -p build
cc -O0 -g -o build/tests src/geom.c check.c
