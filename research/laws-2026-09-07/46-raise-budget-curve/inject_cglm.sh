#!/bin/sh
# the injected cglm defect, reproducible from a pristine copy of cglm:
#   cp -R <cglm> cglm-copy && cmake -S cglm-copy -B cglm-copy/build \
#     -DCGLM_STATIC=ON -DCGLM_USE_TEST=ON -DCMAKE_BUILD_TYPE=Release
#   cmake --build cglm-copy/build -j8
/usr/bin/sed -i '' '944s/glm_clamp(v\[2\]/glm_clamp(v[1]/' \
  "$1/include/cglm/vec3.h"
