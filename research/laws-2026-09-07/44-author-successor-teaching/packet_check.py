#!/usr/bin/env python3
"""packet_check.py <site> <dictfile>

Cheap (one build + one suite run) diagnosis of WHERE a taught class stops:
does the observation packet for the true defect file even contain the
defective line, and does the mechanical observer report the taught kind on
it? No candidate is ever applied, so this costs one suite run, not fifty.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from inject import flip                                    # noqa: E402
from sites import SITES                                    # noqa: E402

from fluidfix import ACTS, KINDS, MechanicalObserver        # noqa: E402
from fluidfix import coracle                                # noqa: E402
from fluidfix.acts import load_dictionary                   # noqa: E402

ROOT = HERE / "cglm"


def main():
    site, dictfile = sys.argv[1], sys.argv[2]
    s = SITES[site]
    saved = dict(KINDS), dict(ACTS)
    assert flip(site, "defect") == 0
    try:
        if dictfile != "none":
            load_dictionary(str(HERE / "dicts" / dictfile))
        o = coracle.COracle(str(ROOT), build_cmd="cmake --build build -j4",
                            test_cmd="./build/tests", timeout=300)
        fails, out = o.failing_output()
        print("suite red?", fails, "| failing tests:",
              (o._fail_tests or [])[:8])
        ranked = coracle.find_candidate_files_c(o, out)
        print("SIGHT ranked files:", ranked)
        print("true defect file in that list?", s["file"] in ranked)
        pk = coracle.build_packet_c(o, s["file"], out)
        if pk is None:
            print("packet: None"); return
        nums = list(pk.lines)
        text = set(nums)
        fl = (ROOT / s["file"]).read_text().split("\n")
        lo = 0
        if s.get("occurrence"):
            lo = next(i for i, l in enumerate(fl)
                      if s["occurrence"] in l and l.startswith("glm_"))
        want = next(i + 1 for i, l in enumerate(fl)
                    if l == s["defect"] and i >= lo)
        print(f"packet lines={len(nums)} range={min(nums)}..{max(nums)}")
        print(f"defect line {want} in packet? {want in text}")
        obs = MechanicalObserver().observe([pk])[0]
        got = [ob for ob in obs if ob.lineno == want]
        print("observation on the defect line:",
              [(ob.lineno, ob.kinds) for ob in got] or "NONE")
        print("total observations in packet:", len(obs))
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
        flip(site, "fixed")


if __name__ == "__main__":
    main()
