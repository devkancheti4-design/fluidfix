#!/usr/bin/env python3
"""inject.py <site> defect|fixed  -- flip one line in the cglm copy.

Prints the file and 1-based line number it changed. Exits 1 if the expected
line is not present (so a silent no-op can never be mistaken for a flip).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES                                    # noqa: E402

ROOT = Path(__file__).parent / "cglm"


def flip(site, want):
    s = SITES[site]
    if s["fixed"] is None:
        print(f"{site}: no site at HEAD"); return 2
    frm = s["fixed"] if want == "defect" else s["defect"]
    to = s["defect"] if want == "defect" else s["fixed"]
    n = 0
    for rel in [s["file"]] + [f for f, _ in s.get("also", [])]:
        p = ROOT / rel
        lines = p.read_text().split("\n")
        # 'maxsign' guard: only the glm_max body, not glm_min's mirror line
        lo = 0
        if s.get("occurrence"):
            lo = next(i for i, l in enumerate(lines) if s["occurrence"] in l
                      and l.startswith("glm_"))
        hits = [i for i, l in enumerate(lines) if l == frm and i >= lo]
        if not hits:
            print(f"NOT FOUND in {rel}: {frm!r}"); return 1
        i = hits[0]
        lines[i] = to
        p.write_text("\n".join(lines))
        print(f"{rel}:{i + 1}  ->  {to}")
        n += 1
    return 0


if __name__ == "__main__":
    sys.exit(flip(sys.argv[1], sys.argv[2]))
