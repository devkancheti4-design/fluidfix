# d_index.py -- ONE taught fault class, written from ONE worked example.
#
# Worked example (cglm cd1f179, "fix rotate make", 2016-11-02):
#     glm_vec_scale(axis_ndc, v[1], m[2]);    <- subscript disagrees with the
#                                                sibling subscript on the line
#     glm_vec_scale(axis_ndc, v[2], m[2]);    <- the fix
#
# The right index is not on the broken line, but it IS in the file (the
# sibling lines use it), so this is a candidate SET mined from repo context
# exactly as docs/TEACHING.md "Candidate sets" prescribes.
import re as _re

_SUB = _re.compile(r"\[(\d+)\]")


def _reindex(line, o):
    subs = list(_SUB.finditer(line))
    if len(subs) < 2:                      # needs a sibling to disagree with
        return [line]                      # not this class: NOPROGRESS
    pool = sorted({m.group(1)
                   for l in (o.all_lines or [line])
                   for m in _SUB.finditer(l)}, key=int)
    out = []
    for m in subs:
        for d in pool:
            if d != m.group(1):
                out.append(line[:m.start(1)] + d + line[m.end(1):])
    return out or [line]


register(
    4,
    "wrong-subscript-index",
    "a constant array subscript that disagrees with the sibling subscripts "
    "used on the same line and on the lines around it",
    _re.compile(r"\[\d+\].*\[\d+\]"),
    _reindex,
)
