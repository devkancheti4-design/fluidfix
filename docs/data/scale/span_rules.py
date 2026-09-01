# span_rules.py — ONE generic taught class for the v0.7 span benchmark.
# Taught from one worked example (two nearby lines drifted together in the
# same incident). Nothing here knows the benchmark sites: candidates are
# combinations of single-token variants of the observed line and one nearby
# line, mined from the file itself, capped, suite-adjudicated.

_CMP = re.compile(r"(?<=[\w\)\]\s])(>=|<=|>|<)(?=[\s\w\(])")
_LIT = re.compile(r"(?<![\w.])(\d+)(?![\w.])")
_TBL = {">=": ">", ">": ">=", "<=": "<", "<": "<="}


def _variants(line, cap=4):
    out = []
    for m in _CMP.finditer(line):
        out.append(line[:m.start(1)] + _TBL[m.group(1)] + line[m.end(1):])
    for m in _LIT.finditer(line):
        v = int(m.group(1))
        for nv in (v - 1, v + 1):
            if nv >= 0:
                out.append(line[:m.start(1)] + str(nv) + line[m.end(1):])
    dedup = []
    for c in out:
        if c != line and c not in dedup:
            dedup.append(c)
    return dedup[:cap]


def _paired_drift(line, o):
    if o.all_lines is None or o.lineno is None:
        return [line]
    i = o.lineno - 1
    mine = _variants(line)
    if not mine:
        return [line]
    out = []
    for d in (1, 2, 3, -1, -2, -3):
        j = i + d
        if not (0 <= j < len(o.all_lines)):
            continue
        theirs = _variants(o.all_lines[j])
        for va in mine:
            for vb in theirs:
                lo, hi = (i, j) if i < j else (j, i)
                block = list(o.all_lines[lo:hi + 1])
                block[i - lo] = va
                block[j - lo] = vb
                out.append(SpanEdit(lo + 1, hi + 1, "\n".join(block)))
    return out or [line]


register(4, "paired-drift",
         "two nearby lines whose tokens drifted together in one incident",
         re.compile(r"[<>]=?|\d"), _paired_drift)
