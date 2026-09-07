#!/bin/sh
# Full rebuild every time: no incremental-staleness confound in this fixture.
set -e
mkdir -p build
cc -O0 -g -o build/tests src/geom.c unittest/main.c
