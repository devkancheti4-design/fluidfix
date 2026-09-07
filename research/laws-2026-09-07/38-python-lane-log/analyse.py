#!/usr/bin/env python3
"""Agent 38 — reduce logs/*.jsonl to the lane tables in REPORT.md."""
import collections
import glob
import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
# The repair BODY. cli.py is EXCLUDED on purpose: `fluidfix selfcheck`
# (cli.py) re-derives all 256 inputs of every law as verification, which is
# not a repair decision and would swamp the lane census.
BODY = {"guard.py", "loop.py", "acts.py", "oracle.py", "coracle.py",
        "localize.py", "observers.py"}

recs = []
for p in sorted(glob.glob(os.path.join(D, "logs", "*.jsonl"))):
    f = os.path.basename(p)[:-6]
    for line in open(p):
        r = json.loads(line)
        r["file"] = f
        recs.append(r)

laws = [r for r in recs if r["law"] != "-"]
body = [r for r in laws if r["site"].split(":")[0] in BODY]
frmtest = [r for r in laws if r["site"].split(":")[0] not in BODY]

print("total law consultations logged: %d" % len(laws))
print("  from the BODY  : %d" % len(body))
print("  from test code : %d  (direct law unit tests)" % len(frmtest))
print()

# ---------------------------------------------------------------- engine ---
print("=" * 78)
print("ENGINE LAW — every ruling the BODY produced, by call site and byte")
print("=" * 78)
eng = [r for r in body if r["law"] == "engine"]
t = collections.Counter((r["site"], r["byte"], "|".join(r["bits"]) or "(none)",
                         r["ruling"]) for r in eng)
print("%-14s %6s %-28s %-24s %7s" % ("site", "byte", "bits", "ruling", "n"))
for (site, b, bits, rul), n in sorted(t.items(), key=lambda kv: -kv[1]):
    print("%-14s 0x%02x   %-28s %-24s %7d" % (site, b, bits, rul, n))
print("\ndistinct engine bytes the body constructed: %s"
      % sorted({r["byte"] for r in eng}))
print("distinct engine rulings the body received : %s"
      % sorted({r["ruling"] for r in eng}))
print("engine consultations from the body        : %d" % len(eng))
sites = collections.Counter(r["site"] for r in eng)
print("per-site counts: %s" % dict(sites))

# --------------------------------------------------------------- outcomes --
print()
print("=" * 78)
print("GUARD RUNS ON PYTHON FIXTURES — lanes hit vs outcome")
print("=" * 78)
runs = []
cur = None
for r in recs:
    ev = r.get("event")
    if ev == "guard_once:enter":
        cur = {"file": r["file"], "test": r["test"], "root": r["root"],
               "files": r.get("files", {}), "engine": [], "sight": [],
               "rank": [], "router": 0, "lanes": 0, "repairs": []}
        runs.append(cur)
    elif cur is None:
        continue
    elif ev == "guard_once:exit":
        cur.update(status=r["status"], gfile=r.get("file"),
                   seconds=r.get("seconds"), hint=r.get("hint", ""),
                   reason=r.get("reason", ""),
                   ncand=len(r.get("candidates") or []))
        cur = None
    elif ev == "guard_once:raise":
        cur.update(status="RAISED", gfile=None, seconds=None,
                   hint=r.get("exc", ""), reason="", ncand=0)
        cur = None
    elif ev in ("repair:exit",):
        cur["repairs"].append(r)
    elif r["law"] == "engine":
        cur["engine"].append(r)
    elif r["law"] == "sight":
        cur["sight"].append(r)
    elif r["law"] == "rank":
        cur["rank"].append(r)
    elif r["law"] == "router":
        cur["router"] += 1
    elif r["law"].startswith("lanes."):
        cur["lanes"] += 1

runs = [r for r in runs if "status" in r]
print("guard_once runs on Python fixtures: %d" % len(runs))
print(collections.Counter(r["status"] for r in runs))
print()
hdr = ("%-46s %-9s %-9s %-30s %-26s" %
       ("test (fixture)", "outcome", "file", "engine bytes -> rulings",
        "sight prios / rank prios"))
print(hdr)
print("-" * len(hdr))
for r in runs:
    eb = ", ".join(sorted({"0x%02x->%s" % (e["byte"], e["ruling"])
                           for e in r["engine"]})) or "-"
    sp = "".join(sorted({str(s["ruling"]) for s in r["sight"]})) or "-"
    rp = "".join(sorted({str(s["ruling"]) for s in r["rank"]})) or "-"
    print("%-46s %-9s %-9s %-30s S:%s R:%s" %
          (r["test"].split("::")[-1][:46], r["status"], (r["gfile"] or "-")[:9],
           eb[:30], sp, rp))

# ------------------------------------------------------------------ sight --
print()
print("=" * 78)
print("SIGHT LAW — bytes the body constructed (guard.py:280)")
print("=" * 78)
sg = [r for r in body if r["law"] == "sight"]
t = collections.Counter((r["site"], r["byte"], "|".join(r["bits"]) or "(none)",
                         r["ruling"]) for r in sg)
for (st, b, bits, rul), n in sorted(t.items(), key=lambda kv: -kv[1]):
    print("%-14s 0x%02x  %-46s prio=%s   n=%d" % (st, b, bits, rul, n))
seen = set()
for r in sg:
    seen.update(r["bits"])
import fluidfix.sight as _S  # noqa: E402
print("SIGHT bits never observed set: %s" % [b for b in _S.BITS if b not in seen])
print("distinct sight priorities emitted: %s" % sorted({r["ruling"] for r in sg}))

# ------------------------------------------------------------------- rank --
print()
print("=" * 78)
print("RANKING LAW — bytes the body constructed (guard.py:406)")
print("=" * 78)
rk = [r for r in body if r["law"] == "rank"]
t = collections.Counter((r["site"], r["byte"], "|".join(r["bits"]) or "(none)",
                         r["ruling"]) for r in rk)
for (st, b, bits, rul), n in sorted(t.items(), key=lambda kv: -kv[1]):
    print("%-14s 0x%02x  %-46s prio=%s   n=%d" % (st, b, bits, rul, n))
seen = set()
for r in rk:
    seen.update(r["bits"])
import fluidfix.rank as _R  # noqa: E402
print("RANK bits never observed set: %s" % [b for b in _R.BITS if b not in seen])
print("distinct rank priorities emitted: %s" % sorted({r["ruling"] for r in rk}))

# ----------------------------------------------------------------- router --
print()
print("=" * 78)
print("FLUID-ROUTER (acts.py:319) and LANES (loop.py:284/297/298)")
print("=" * 78)
ro = [r for r in body if r["law"] == "router"]
print("route() calls from the body: %d" % len(ro))
print("distinct (F1,A1,Fq) queried: %s"
      % sorted({tuple(r["byte"]) for r in ro}))
print("distinct act codes returned: %s" % sorted({r["ruling"] for r in ro}))
ln = [r for r in body if r["law"].startswith("lanes.")]
print("lanes calls from the body: %s"
      % dict(collections.Counter(r["law"] for r in ln)))
print("distinct HALT results: %s"
      % sorted({r["ruling"] for r in ln if r["law"] == "lanes.HALT"}))
print("distinct EMIT results: %s"
      % sorted({r["ruling"] for r in ln if r["law"] == "lanes.EMIT"}))
