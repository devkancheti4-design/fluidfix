import json, difflib, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad")
from verify_l23 import ORIG, TESTS, check_additions_only

path = "/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/answers_l23.json"
data = json.load(open(path))
assert set(data) == {"level2", "level3"}, data.keys()

ok = True
for level in ("level2", "level3"):
    assert set(data[level]) == set(ORIG), f"{level} keys mismatch: {set(data[level])}"
    for cid, src in data[level].items():
        if src == "IMPOSSIBLE":
            print(f"{level:7} {cid:32} IMPOSSIBLE"); continue
        if level == "level2":
            clean, bad = check_additions_only(ORIG[cid], src)
            if not clean:
                ok = False
                print(f"{level:7} {cid:32} ADDITIONS-ONLY VIOLATED: {bad}")
        ns = {}
        try:
            exec(compile(src, cid, "exec"), ns)
            exec(compile(TESTS[cid], cid + ":tests", "exec"), ns)
            extra = " (additions-only OK)" if level == "level2" else ""
            print(f"{level:7} {cid:32} PASS{extra}")
        except Exception as e:
            ok = False
            print(f"{level:7} {cid:32} FAIL {type(e).__name__}: {e}")
print("\nFINAL: ALL GOOD" if ok else "\nFINAL: PROBLEMS")
