"""Turn a probe.py dump into the progress-rate curve + the pollution number.

usage: analyse.py DUMP.json [BUCKET_SECONDS]
"""
import json, sys, collections

d = json.load(open(sys.argv[1]))
B = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
rows = d["rows"]
print("== run:", sys.argv[1])
print("suite runs judged (probe rows):", len(rows))
if not rows:
    sys.exit(0)
print("span: %.1fs .. %.1fs" % (rows[0]["t"], rows[-1]["t"]))

# ---- phase split
ph = collections.Counter(r["phase"] for r in rows)
print("\n-- rows per phase:", dict(ph))
for p in ("pass0", "escalation"):
    rs = [r for r in rows if r["phase"] == p]
    if not rs:
        continue
    wall = rs[-1]["t"] - rs[0]["t"] + rs[-1]["dur"]
    tot = sum(r["dur"] for r in rs)
    print("  %-10s n=%4d  t=%7.1f..%7.1f  wall=%6.1fs  "
          "suite-time=%6.1fs (%.0f%%)  rate=%.3f cand/s  mean run=%.2fs"
          % (p, len(rs), rs[0]["t"], rs[-1]["t"], wall, tot,
             100 * tot / wall if wall else 0,
             len(rs) / wall if wall else 0, tot / len(rs)))

# ---- REPEATED WORK: identical mutated file content re-tested
seen, dup_rows, first_seen = {}, [], {}
for r in rows:
    k = (r["file"], r["sha"])
    if k in seen:
        dup_rows.append((r, first_seen[k]))
    else:
        seen[k] = 1
        first_seen[k] = r
print("\n-- repeated work (identical mutated file content re-tested)")
print("  distinct candidate programs: %d of %d rows" % (len(seen), len(rows)))
print("  repeated rows: %d (%.1f%% of all suite runs)"
      % (len(dup_rows), 100.0 * len(dup_rows) / len(rows)))
print("  wall clock burned on repeats: %.1fs of %.1fs suite time (%.1f%%)"
      % (sum(r["dur"] for r, _ in dup_rows), sum(r["dur"] for r in rows),
         100.0 * sum(r["dur"] for r, _ in dup_rows)
         / max(sum(r["dur"] for r in rows), 1e-9)))
xph = collections.Counter((f["phase"], r["phase"]) for r, f in dup_rows)
for (a, b), n in sorted(xph.items()):
    print("    first tried in %-10s re-tried in %-10s : %d" % (a, b, n))
esc = [r for r in rows if r["phase"] == "escalation"]
if esc:
    escdup = [r for r, f in dup_rows if r["phase"] == "escalation"]
    print("  ESCALATION: %d of %d of its suite runs (%.1f%%) re-test a "
          "program pass0 already judged" % (len(escdup), len(esc),
                                            100.0 * len(escdup) / len(esc)))
    if escdup:
        last = max(r["t"] + r["dur"] for r in escdup)
        firstnew = min((r["t"] for r in esc
                        if (r["file"], r["sha"]) not in
                        {(x["file"], x["sha"]) for x in rows
                         if x["phase"] == "pass0"}), default=None)
        print("  escalation's FIRST candidate pass0 had not already judged: "
              "t=%s (escalation began at t=%.1f)"
              % (("%.1f" % firstnew) if firstnew is not None else "none",
                 esc[0]["t"]))

# ---- the curve, bucketed
print("\n-- progress-rate curve (%.0fs buckets): cum = cumulative suite-judged"
      "\n   candidates; new = cumulative DISTINCT programs" % B)
print("   %8s %6s %6s %6s %8s %s" %
      ("t_end", "n", "cum", "new", "cand/s", "phase(s)"))
seen2, cum, new = set(), 0, 0
b = B
i = 0
while i < len(rows):
    n = 0
    phs = set()
    while i < len(rows) and rows[i]["t"] < b:
        r = rows[i]
        n += 1; cum += 1
        k = (r["file"], r["sha"])
        if k not in seen2:
            seen2.add(k); new += 1
        phs.add(r["phase"]); i += 1
    print("   %8.0f %6d %6d %6d %8.3f %s"
          % (b, n, cum, new, n / B, "+".join(sorted(phs)) or "-"))
    b += B

# ---- law rulings
print("\n-- engine law rulings observed")
for l in d["law"]:
    print("   t=%7.1f  %-10s bits=%-28s -> %s"
          % (l["t"], l["phase"], ",".join(l["bits"]) or "(none)", l["act"]))

print("\n-- repair() calls")
for r in d["repairs"]:
    print("   %-10s %-24s t=%7.1f..%7.1f runs=%4d repaired=%s obs=%d "
          "log=%d more=%d" % (r["phase"], r["rel"], r["t_start"], r["t_end"],
                              r["runs_logged"], r["repaired"], r["n_obs"],
                              r["tried_log"], r["tried_more"]))
