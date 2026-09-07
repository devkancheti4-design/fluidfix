#!/usr/bin/env python3
"""The six REAL one-token cglm fixes from git history, mapped to HEAD.

Each entry: the historical commit, the file at HEAD, the FIXED line (what
HEAD has today) and the DEFECT line (what the commit removed) -- i.e. we
re-inject exactly the defect the maintainer really fixed.
"""
SITES = {
    "refract": dict(
        commit="48839a3", subject="fix refract",
        file="include/cglm/vec3.h",
        fixed="  k   = 1.0f - eta * eta + eni * eni;",
        defect="  k   = 1.0f + eta * eta - eni * eni;",
        # the real commit flipped the identical line in vec2.h/vec4.h too;
        # we inject ONE line so this stays a single-edit repair problem.
    ),
    "transform": dict(
        commit="340292c", subject="fix transform",
        file="include/cglm/aabb2d.h",
        fixed="  glm_vec2(m[2], v[0]);",
        defect="  glm_vec2(m[3], v[0]);",
    ),
    "frustum": dict(
        commit="40458be", subject="frustum: fix array index",
        file="include/cglm/frustum.h",
        fixed="  glm_vec4_scale(c[0], 1.0f / c[0][3], dest[0]);",
        defect="  glm_vec4_scale(c[0], 1.0f / c[1][3], dest[0]);",
    ),
    "maxsign": dict(
        commit="3e4f52b", subject="optimize operations, fix max sign",
        file="include/cglm/util.h",
        fixed="  if (a > b)",
        defect="  if (a < b)",
        occurrence="glm_max",
    ),
    "rotatemake": dict(
        commit="cd1f179", subject="fix rotate make",
        file="include/cglm/affine.h",
        fixed="  glm_vec3_scale(axisn, v[2], m[2]);",
        defect="  glm_vec3_scale(axisn, v[1], m[2]);",
    ),
    "euler": dict(
        commit="005a6f5", subject="fix euler angle val",
        file="include/cglm/euler.h",
        fixed=None,          # site does not exist at HEAD (see REPORT.md F2)
        defect=None,
    ),
}
