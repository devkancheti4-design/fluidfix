#!/usr/bin/env python3
"""Python maintenance arm: for each case, reset to the green base, ship the
regression as a commit, confirm the suite is red, run the guard exactly as the
maintenance loop would (`fluidfix guard . --commit --dictionary rules.py`),
then score against the PRISTINE BYTES — never against "the suite is green".
usage: run_py.py <ledgerkit-repo> <out.json>"""
import json, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from catalog import CASES
PYBIN = "/Library/Frameworks/Python.framework/Versions/3.14/bin"
FF = os.path.join(PYBIN, "fluidfix")
RULES = os.path.join(HERE, "rules.py")
root, out = sys.argv[1], sys.argv[2]
# --master runs the checked-out source tree instead of the installed package;
# --cases R03,R13 restricts the run. Both are recorded in the output.
MASTER = "--master" in sys.argv
ONLY = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--cases=")), None)
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "src"))

def sh(*a, env=None, timeout=None, check=True):
    return subprocess.run(a, cwd=root, capture_output=True, text=True, env=env,
                          timeout=timeout, check=check)
def git(*a, **k): return sh("git", *a, **k).stdout.strip()
def clear_pyc():
    for d, dirs, _ in os.walk(root):
        for x in list(dirs):
            if x == "__pycache__": shutil.rmtree(os.path.join(d, x)); dirs.remove(x)
def pytest_status():
    clear_pyc()
    r = sh(os.path.join(PYBIN, "python3"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", check=False)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""

BASE = git("rev-parse", "HEAD")
results = []
for c in [c for c in CASES if not ONLY or c["id"] in ONLY]:
    git("reset", "-q", "--hard", BASE); git("clean", "-qfdx"); clear_pyc()
    rec = dict(id=c["id"], kind=c["kind"], file=c["file"], expect=c["expect"])
    if c["file"]:
        p = os.path.join(root, c["file"]); src = open(p).read()
        assert src.count(c["old"]) == 1, (c["id"], src.count(c["old"]))
        defect = src.replace(c["old"], c["new"]); open(p, "w").write(defect)
        pristine = git("show", f"{BASE}:{c['file']}") + "\n"
        pristine = src  # exact bytes as on disk at base
        git("commit", "-qam", f"{c['id']}: teammate ships ({c['kind']})")
        rc, last = pytest_status(); rec["red_before"] = (rc != 0); rec["pytest_before"] = last
        if rc == 0:
            rec["verdict"] = "INVALID_CASE (suite not red)"; results.append(rec); print(rec); continue
    else:
        rc, last = pytest_status(); rec["red_before"] = (rc != 0); rec["pytest_before"] = last
    env = dict(os.environ, PATH=PYBIN + ":" + os.environ["PATH"], **c.get("env", {}))
    t0 = time.time()
    try:
        if MASTER: env["PYTHONPATH"] = SRC
        cmd = ([os.path.join(PYBIN, "python3"), "-c", "from fluidfix.cli import main; raise SystemExit(main())"] if MASTER else [FF])
        r = sh(*cmd, "guard", ".", "--commit", "--dictionary", RULES, env=env, timeout=420, check=False)
        outp, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        outp, code = (e.stdout or "") + (e.stderr or "") + "\n[TIMEOUT 420s]", 124
    rec["seconds_wall"] = round(time.time() - t0, 1); rec["exit"] = code
    m = re.search(r"repaired line (\d+) in (\d+) suite runs \(([\d.]+)s\)", outp)
    rec["repaired_line"], rec["suite_runs"], rec["seconds_reported"] = (int(m[1]), int(m[2]), float(m[3])) if m else (None, None, None)
    rec["output_head"] = "\n".join(l for l in outp.splitlines() if l.strip())[:700]
    ref = os.path.join(root, ".fluidfix", "last_refusal.json")
    if os.path.exists(ref):
        j = json.load(open(ref)); rec["ruling"] = j.get("ruling"); rec["hint"] = (j.get("hint") or "")[:160]
        rec["rejected"] = len(j.get("rejected_candidates", []))
    rec["pin_me_test"] = os.path.exists(os.path.join(root, ".fluidfix", "pin_me_test.py"))
    rec["tree_clean"] = git("status", "--porcelain") == ""
    rec["head_subject"] = git("log", "-1", "--format=%s")
    if c["file"]:
        now = open(os.path.join(root, c["file"])).read()
        rec["bytes_pristine"] = (now == pristine); rec["bytes_defect"] = (now == defect)
    e = c["expect"]
    if e == "repair":
        v = "BYTE_EXACT" if (code == 0 and rec["bytes_pristine"]) else ("GREEN_DIFFERENT" if code == 0 else "REFUSED (miss)")
    elif e == "refuse":
        v = "CORRECT_REFUSAL" if (code == 2 and rec["bytes_defect"] and rec["tree_clean"]) else f"SHIPPED_ON_REFUSE_CASE exit={code} pristine={rec.get('bytes_pristine')}"
    else:
        v = "GREEN_NOOP" if ("suite green" in outp and code == 0) else f"UNEXPECTED exit={code}"
    rec["verdict"] = v; results.append(rec)
    print(f"{c['id']:4} {c['kind']:<46} exit={code} {rec['seconds_wall']:>5}s runs={rec['suite_runs']} -> {v}", flush=True)
git("reset", "-q", "--hard", BASE); git("clean", "-qfdx")
json.dump(dict(base=BASE, source=("master:" + subprocess.run(["git", "-C", SRC, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()) if MASTER else subprocess.run([FF, "--version"], capture_output=True, text=True).stdout.strip(),
               cases=results), open(out, "w"), indent=1)
tally = {}
for r in results: tally[r["verdict"].split(" ")[0]] = tally.get(r["verdict"].split(" ")[0], 0) + 1
print("TALLY", tally)
