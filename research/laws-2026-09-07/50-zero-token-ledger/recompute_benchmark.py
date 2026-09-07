import json, collections
D = json.load(open("/Users/kanchetidevieswar/neo/fluidfix/docs/data/arm_a_full_results.json"))
print("records:", len(D))
bugs = sorted({r["n"] for r in D})
print("distinct bug ids:", len(bugs))
for v in ("v1", "v2"):
    rs = [r for r in D if r["variant"] == v]
    iv = [r for r in rs if r["in_vocab"]]
    oov = [r for r in rs if not r["in_vocab"]]
    print(f"--- variant {v}: {len(rs)} recs, in_vocab {len(iv)}, oov {len(oov)}")
    print("   in-vocab byte-exact:", sum(1 for r in iv if r.get("exact")), "/", len(iv))
    print("   in-vocab repaired  :", sum(1 for r in iv if r.get("repaired")), "/", len(iv))
    print("   in-vocab green-only:", sum(1 for r in iv if r.get("repaired") and not r.get("exact")))
    print("   oov refused        :", sum(1 for r in oov if r.get("refused")), "/", len(oov))
    print("   loc_correct        :", sum(1 for r in rs if r.get("loc_correct")), "/", len(rs))
    print("   total suite_runs   :", sum(r.get("suite_runs", 0) for r in rs))
    print("   total secs         :", round(sum(r.get("secs", 0) for r in rs), 1))
# localisation across distinct bugs
loc = {}
for r in D:
    loc[r["n"]] = loc.get(r["n"], False) or r.get("loc_correct", False)
print("distinct bugs with loc_correct:", sum(1 for v in loc.values() if v), "/", len(loc))
