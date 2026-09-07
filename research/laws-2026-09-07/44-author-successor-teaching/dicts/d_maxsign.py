# d_maxsign.py -- ONE taught fault class, from ONE worked example.
#
# Worked example (cglm 3e4f52b, "optimize operations, fix max sign",
# 2018-01-02, include/cglm/util.h glm_max):
#     if (a < b)      <- comparison points the wrong way
#     if (a > b)      <- the fix
#
# A pure rule over the line: ONE string candidate.
import re as _re


def _flip_cmp(line, o):
    if "<" in line and ">" not in line:
        return [line.replace("<", ">")]
    if ">" in line and "<" not in line:
        return [line.replace(">", "<")]
    return [line]                            # not this class: NOPROGRESS


register(
    4,
    "flipped-comparison-direction",
    "a comparison whose direction is reversed: a < that should be a > "
    "(or the other way round), operands already in the right order",
    _re.compile(r"[<>]"),
    _flip_cmp,
)
