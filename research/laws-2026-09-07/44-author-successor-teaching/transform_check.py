#!/usr/bin/env python3
"""Stage-1 check, zero suite runs (docs/TEACHING.md "0:15 ... exercise the
transform without running any suite").

For each of the six historical cglm fixes: load the dictionary taught from
THAT one worked example, hand the taught transform the re-injected defect
line with real repo context, and report whether the historically-correct
fixed line is among the candidates it emits (and at what rank).
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from sites import SITES                                    # noqa: E402

from fluidfix import ACTS, KINDS, Observation              # noqa: E402
from fluidfix.acts import act_for, candidates, load_dictionary  # noqa: E402

ROOT = HERE / "cglm"
DICT = {"refract": "d_refract.py", "maxsign": "d_maxsign.py",
        "transform": "d_index.py", "frustum": "d_index.py",
        "rotatemake": "d_index.py", "euler": "d_index.py"}

# The euler site is gone from HEAD; reconstruct its context from the
# historical file so the class can still be exercised on the real defect.
EULER_HIST = """      float a[2][3];
      int   path;

      a[0][1] = asinf(m[2][0]);
      a[1][1] = M_PI - a[0][0];

      cy1 = cosf(a[0][1]);
      cy2 = cosf(a[1][1]);
""".split("\n")


def one(site):
    s = SITES[site]
    saved = dict(KINDS), dict(ACTS)
    try:
        load_dictionary(str(HERE / "dicts" / DICT[site]))
        if site == "euler":
            lines = EULER_HIST
            lineno = 5
            broken = "      a[1][1] = M_PI - a[0][0];"
            want = "      a[1][1] = M_PI - a[0][1];"
        else:
            lines = (ROOT / s["file"]).read_text().split("\n")
            broken, want = s["defect"], s["fixed"]
            lineno = lines.index(want) + 1
            lines[lineno - 1] = broken
        obs = Observation(lineno=lineno, all_lines=lines, file=s["file"],
                          root=str(ROOT))
        cs = candidates(broken, act_for(4), obs)
        rank = cs.index(want) + 1 if want in cs else None
        print(f"{site:11s} dict={DICT[site]:12s} candidates={len(cs):3d} "
              f"correct_fix={'YES rank %d' % rank if rank else 'NO'}")
        if rank is None:
            print(f"            emitted: {cs[:6]}")
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])


if __name__ == "__main__":
    for k in SITES:
        one(k)
