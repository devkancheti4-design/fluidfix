"""Run the REAL guard over the corpus and score each outcome against intent.

Scored on what ended up on disk, not on whether the suite went green — a wrong
repair also makes the suite green, which is the entire problem.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus import CASES

PY = sys.executable
FF = str(pathlib.Path(__file__).resolve().parents[2] / ".venv" / "bin" / "fluidfix")

def validate(case):
    """A case is only usable if the suite is GREEN on the pristine module and RED
    on the defect. Two of the first corpus's cases failed this — one imported a
    name that did not exist, one had a "defect" no assertion could see — and
    scoring them would have reported my bugs as the tool's."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="val-"))
    (d/"test_mod.py").write_text(case["tests"])
    def suite(src):
        # Clear __pycache__ first. A one-token edit keeps the file the SAME SIZE,
        # and if both writes land in the same second Python reuses the stale
        # bytecode — so the defect silently never takes effect and the case looks
        # invalid. fluidfix's own oracle calls clear_pyc() for exactly this; the
        # first version of this harness did not, and wrongly rejected 10 of 15
        # good cases.
        for pc in d.rglob("__pycache__"): shutil.rmtree(pc, ignore_errors=True)
        (d/"mod.py").write_text(src)
        r = subprocess.run([PY,"-m","pytest","-q","--no-header","-p","no:cacheprovider"],
                           cwd=d, capture_output=True, text=True, timeout=120)
        return r.returncode == 0, r.stdout[-300:]
    green_ok, g_out = suite(case["module"])
    red_ok,  r_out  = suite(case["module"].replace(case["pristine"], case["defect"]))
    shutil.rmtree(d, ignore_errors=True)
    if not green_ok: return False, "pristine module does not pass its own suite: "+g_out.strip()[-120:]
    if red_ok:       return False, "defect does not break the suite (nothing to repair)"
    return True, ""

def run(case):
    d = pathlib.Path(tempfile.mkdtemp(prefix="ff-"))
    (d/"mod.py").write_text(case["module"].replace(case["pristine"], case["defect"]))
    (d/"test_mod.py").write_text(case["tests"])
    pristine_file = case["module"]
    t0 = time.time()
    p = subprocess.run([FF, "guard", ".", "--python", PY, "--budget", "120"],
                       cwd=d, capture_output=True, text=True, timeout=300)
    secs = time.time() - t0
    after = (d/"mod.py").read_text()
    changed = after != case["module"].replace(case["pristine"], case["defect"])
    correct = after == pristine_file
    # what a `push` default would have committed
    if not changed:
        outcome = "green" if "nothing to do" in p.stdout or "suite green" in p.stdout else "refused"
    else:
        outcome = "repaired_correct" if correct else "repaired_WRONG"
    shutil.rmtree(d, ignore_errors=True)
    return dict(name=case["name"], expect=case["expect"], outcome=outcome,
                secs=round(secs,1), why=case["why"],
                line=[l for l in after.splitlines() if l.strip()][:99][
                     max(0,0)] if False else None)

def verdict(expect, outcome):
    if expect == "repair_correct":  return "OK" if outcome=="repaired_correct" else "MISS"
    if expect == "refuse":          return "OK" if outcome in ("refused","green") else "BAD"
    if expect == "green":           return "OK" if outcome in ("green","refused") else "BAD"
    if expect == "either":          return "OK" if outcome!="repaired_WRONG" else "BAD"
    return "?"

rows=[]; broken=[]
for c in CASES:
    ok, why = validate(c)
    if not ok:
        broken.append((c["name"], why))
        print(f"SKIP {c['name']:24s} INVALID CASE - {why}", flush=True)
        continue
    r = run(c); r["verdict"] = verdict(c["expect"], r["outcome"])
    rows.append(r)
    print(f"{r['verdict']:4s} {r['name']:24s} expect={r['expect']:16s} got={r['outcome']:18s} {r['secs']:>5}s", flush=True)

out = pathlib.Path(__file__).parent / "results.json"
out.write_text(json.dumps(rows, indent=1))
n=len(rows)
if broken:
    print(f"\n{len(broken)} case(s) excluded as invalid BEFORE scoring:")
    for b in broken: print("   ", b[0], "-", b[1])
print()
wrong=[r for r in rows if r["outcome"]=="repaired_WRONG"]
print()
print(f"cases                : {n}")
print(f"repaired correctly   : {sum(1 for r in rows if r['outcome']=='repaired_correct')}")
print(f"REPAIRED WRONG       : {len(wrong)}   <- what `mode: push` would commit")
print(f"refused / left alone : {sum(1 for r in rows if r['outcome'] in ('refused','green'))}")
print(f"verdicts             : OK {sum(1 for r in rows if r['verdict']=='OK')}  "
      f"MISS {sum(1 for r in rows if r['verdict']=='MISS')}  BAD {sum(1 for r in rows if r['verdict']=='BAD')}")
for w in wrong: print("   WRONG:", w["name"], "-", w["why"])
