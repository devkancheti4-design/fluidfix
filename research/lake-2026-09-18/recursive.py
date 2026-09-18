#!/usr/bin/env python3
"""The recursive model: the same organ at every level — cheapest first, remember what won, abstain when absent.

Fused from two of the author's repositories, both AGPL-3.0, both carrying the SAME memory core (life.py,
sha256-identical in each):

  github.com/devkancheti4-design/life-debugger   the ladder and the memory: known patterns free, memory free,
                                                a model only for the genuinely new — and the answer is kept.
  github.com/devkancheti4-design/living-fused    the confidence gate as a ROUTER: what the memory knows
                                                confidently is answered with ZERO expensive calls, and the
                                                expensive calls are COUNTED so "zero" is a fact, not a claim.

Here the expensive call is not a model forward: it is a dispatched fluidfix and the suite runs it pays for.

Level 0, inside one fluidfix: the shipped and taught vocabulary decides, the suite judges, and a refusal is
reported rather than guessed. That is the product.

Level 1, the judge over N fluidfixes: Life keyed by the failure signature -> "territory|kind", read through
the confidence gate w = t/(t+C). w >= THRESH dispatches exactly ONE fluidfix and pays one guard. An absent
key scores 0.0 and abstains into the cold fan-out: one fluidfix per (territory, kind), scarcest classes
first, first green ends it, and the winner is learned.

Level 2, the same organ at a coarser key: "winners" -> kind, a count table over the classes that have ever
answered. A signature never seen before still inherits the ORDER of the fan-out from it, so the lesson
crosses repositories even though the signature does not. A judge over judges would key it by repository and
change nothing else. That is what makes it recursive.

  PYTHONPATH=<fluidfix>/src python3 recursive.py <clones-root> rich/lenm1-1 \\
      --template <clone> --dictionary <rules.py> [--territories 8] [--kinds-per-territory 3] [--cold]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from life import Life                                                    # noqa: E402

CASES = HERE.parent / "llm-fusion-2026-09-16" / "cases"
SRC = HERE.parents[1] / "src"
MEMORY = HERE / "judge_memory.json"

# one small fluidfix: one territory, one kind, full sight of its own file
DRIVER = """
import sys
src, rel, dictionary, kind = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary, KINDS
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
if dictionary:
    load_dictionary(dictionary)
o = Oracle(".", python=sys.executable)
red, out = o.failing_output()
if not red:
    print("suite green"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10 ** 9)
if pk is None:
    print("no packet"); raise SystemExit(3)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
mine = []
for x in obs:
    if kind in x.kinds:
        x.kinds = [kind]
        mine.append(x)
print(f"routed: kind {kind} x {rel}: {len(mine)} of {len(obs)} observations", flush=True)
if not mine:
    print("refused: nothing in this territory can exhibit this class"); raise SystemExit(2)
res = repair(o, rel, mine)
print(f"suite_runs={res.suite_runs}")
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""

# what the failing test EXECUTED, and which kinds each file can exhibit — one suite run, no ranking
SURVEY = """
import json, os, sys
src, dictionary = sys.argv[1], sys.argv[2]
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary, KINDS
from fluidfix.guard import _is_test_path
if dictionary:
    load_dictionary(dictionary)
o = Oracle(".", python=sys.executable)
red, out = o.failing_output()
first = next((l.strip() for l in out.splitlines() if l.startswith("FAILED")), "")
cov = "_rec_cov.json"
o.run(["--lf", "--tb=no", "--cov=.", f"--cov-report=json:{cov}"], cache=True)
files = {}
if os.path.exists(cov):
    d = json.load(open(cov)); os.remove(cov)
    for f, data in d.get("files", {}).items():
        rel = f.replace("\\\\", "/")
        lines = data.get("executed_lines", [])
        if not lines or not rel.endswith(".py") or _is_test_path(rel) or "site-packages" in rel or "/.venv/" in rel:
            continue
        try:
            src_lines = open(rel, encoding="utf-8", errors="replace").read().split("\\n")
        except OSError:
            continue
        per = {}
        for k, entry in KINDS.items():
            sig = entry[2]
            if sig is None:
                continue
            hits = sum(1 for l in lines if 0 < l <= len(src_lines) and sig.search(src_lines[l - 1]))
            if hits:
                per[k] = hits
        files[rel] = {"executed": len(lines), "kinds": per}
print(json.dumps({"red": red, "failing": first, "files": files}))
"""


def sh(cmd, cwd=None, env=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def apply_mutation(clone: Path, mut: dict, commit=True):
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=clone)
    sh(["git", "clean", "-fdq", "-e", ".venv"], cwd=clone)
    p = clone / mut["file"]
    lines = p.read_text(encoding="utf-8", newline="").split("\n")
    assert lines[mut["lineno"] - 1] == mut["orig"], f"{clone.name}: base line drifted"
    lines[mut["lineno"] - 1] = mut["mutated"]
    p.write_text("\n".join(lines), encoding="utf-8", newline="")
    if commit:
        sh(["git", "-c", "user.name=rec", "-c", "user.email=rec@fluidfix", "commit", "-qam", "recursive: inject"], cwd=clone)
    shutil.rmtree(clone / ".fluidfix", ignore_errors=True)


def make_clone(template: Path, dest: Path):
    if dest.exists():
        return
    shutil.copytree(template, dest, symlinks=True)
    (dest / ".git" / "index.lock").unlink(missing_ok=True)
    for pth in list((dest / ".venv").rglob("*.pth")) + [dest / ".venv" / "pyvenv.cfg"]:
        if pth.name == "a1_coverage.pth" or not pth.exists():
            continue
        try:
            t = pth.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if str(template) in t:
            pth.write_text(t.replace(str(template), str(dest)))


def launch(clone: Path, rel: str, kind: int, dictionary: str, env):
    py = str(clone / ".venv" / "bin" / "python")
    return subprocess.Popen([py, "-c", DRIVER, str(SRC), rel, dictionary or "", str(kind)],
                            cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("case"); ap.add_argument("--template", required=True)
    ap.add_argument("--dictionary"); ap.add_argument("--territories", type=int, default=8)
    ap.add_argument("--kinds-per-territory", type=int, default=0,
                    help="0 = every class the territory can exhibit (a fan-out must cover, not rank)")
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--cold", action="store_true", help="ignore and reset the judge's memory for this signature")
    ap.add_argument("--thresh", type=float, default=0.5, help="confidence gate: at or above this, dispatch one guard")
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    template = Path(a.template).resolve(); root = Path(a.root).resolve(); root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    life = Life(str(MEMORY))

    # ---- one survey run: what the failing test executed, and which classes each file can exhibit
    t_survey = time.time()
    apply_mutation(template, mut, commit=False)
    r = sh([str(template / ".venv" / "bin" / "python"), "-c", SURVEY, str(SRC), a.dictionary or ""],
           cwd=template, env=env, timeout=900)
    survey = json.loads(r.stdout.strip().splitlines()[-1])
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=template)
    survey_s = round(time.time() - t_survey, 1)
    sig = f"{repo_name}::{survey['failing'].split(' ')[1] if ' ' in survey['failing'] else survey['failing']}"
    conf = 0.0 if a.cold else life.confidence(sig)
    known = life.recall(sig) if (not a.cold and conf >= a.thresh) else None
    if a.cold:
        life.forget(sig)
    # level 2: the classes that have answered before, most recent first (recency-dominant counts)
    prior = [int(v.split(":")[1]) for v, _c in reversed(life.history("winners")) if v.startswith("kind:")]
    print(f"[{a.case}] signature {sig}", flush=True)
    print(f"[{a.case}] survey {survey_s}s: {len(survey['files'])} files executed by the failing test; "
          f"memory: confidence {conf:.3f} (gate {a.thresh}) -> {known or 'ABSTAIN, fan out'}"
          f"{'; classes that answered before: ' + str(prior) if prior and not known else ''}", flush=True)

    # ---- dispatch: one guard if the memory knows, else the sparse fan-out it will learn from
    plan = []
    if known:
        rel, k = known.rsplit("|", 1)
        plan = [(rel, int(k))]
    else:
        files = sorted(survey["files"].items(), key=lambda kv: -kv[1]["executed"])[: a.territories]
        for rel, info in files:
            # order: classes that have answered before (level-2 memory), then the scarcest here — a class
            # matching few lines in this territory is the cheapest question to ask.
            ks = sorted(info["kinds"].items(), key=lambda kv: (0 if int(kv[0]) in prior else 1,
                                                              prior.index(int(kv[0])) if int(kv[0]) in prior else 0,
                                                              kv[1]))
            for k, _hits in (ks[: a.kinds_per_territory] if a.kinds_per_territory else ks):
                plan.append((rel, int(k)))
    print(f"[{a.case}] dispatching {len(plan)} fluidfix{'' if len(plan) == 1 else 'es'}"
          f"{' from memory' if known else ' (cold fan-out)'}", flush=True)

    procs = {}
    t0 = time.time()
    for i, (rel, k) in enumerate(plan):
        clone = root / f"{repo_name}_t{i:02d}"
        make_clone(template, clone)
        apply_mutation(clone, mut)
        procs[(rel, k)] = (clone, time.time(), launch(clone, rel, k, a.dictionary, env))

    pending = dict(procs); first_green = None; cancelled = []
    deadline = time.time() + a.timeout
    while pending and time.time() < deadline:
        for key, (clone, ts, pr) in list(pending.items()):
            if pr.poll() is None:
                continue
            del pending[key]
            if pr.returncode == 0 and first_green is None:
                first_green = (key, round(time.time() - t0, 1))
                print(f"  first green: {key[0]} kind {key[1]} at {first_green[1]}s", flush=True)
                deadline = time.time()
        if first_green:
            break
        time.sleep(0.3)
    for key, (clone, ts, pr) in pending.items():
        if pr.poll() is None:
            pr.kill(); cancelled.append(key)

    guards = {}
    for key, (clone, ts, pr) in procs.items():
        try:
            out, _ = pr.communicate(timeout=60); code = pr.returncode
        except subprocess.TimeoutExpired:
            pr.kill(); out, code = "TIMEOUT", 124
        if key in cancelled:
            code = 125
        line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out or "")
        rr = re.search(r"suite_runs=(\d+)", out or "")
        o = re.search(r"routed: kind \d+ x \S+: (\d+) of (\d+)", out or "")
        guards[f"{key[0]}|{key[1]}"] = {"exit": code, "seconds": round(time.time() - ts, 1),
                                        "observations": int(o.group(1)) if o else None,
                                        "suite_runs": int(m.group(2)) if m else (int(rr.group(1)) if rr else None),
                                        "byte_exact": code == 0 and line == mut["orig"]}
    wall = round(time.time() - t0, 1)
    winner = next((k for k, g in guards.items() if g["exit"] == 0), None)
    verdict = "EXACT" if winner and guards[winner]["byte_exact"] else ("WRONG-GREEN" if winner else "REFUSED")

    # ---- the judge learns: this signature was answered by that territory and that class
    learned = None
    if winner and verdict == "EXACT":
        learned = life.learn(sig, winner)
        rel, k = winner.rsplit("|", 1)
        life.learn("winners", f"kind:{k}")   # level 2: the class that answered, for signatures not yet seen
        life.link(sig, f"kind:{k}")
        life.link(f"kind:{k}", f"file:{rel}")
        life.save()
    runs = sum(g["suite_runs"] or 0 for g in guards.values())
    res = {"case": a.case, "signature": sig, "memory_hit": bool(known), "recalled": known, "dispatched": len(plan),
           "confidence_before": round(conf, 3), "gate": a.thresh, "class_prior": prior,
           "guards_launched": len(plan), "suite_runs_paid": runs, "memory_rows": len(life.store),
           "memory_bytes": len(life.dumps().encode()),
           "survey_s": survey_s, "wall_s": wall, "cpu_sum_s": round(sum(g["seconds"] for g in guards.values()), 1),
           "winner": winner, "verdict": verdict, "winner_runs": guards[winner]["suite_runs"] if winner else None,
           "cancelled": [f"{r}|{k}" for r, k in cancelled], "learned": learned,
           "memory_confidence": round(life.confidence(sig), 3), "chain": life.chain(sig), "guards": guards}
    tag = "warm" if known else "cold"
    (HERE / f"recursive_{repo_name}_{cid}_{tag}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] JUDGE ({tag}): {verdict} | winner {winner} in {res['winner_runs']} suite runs | "
          f"fluidfixes dispatched {len(plan)}, suite runs paid {runs} | wall {wall}s cpu-sum {res['cpu_sum_s']}s",
          flush=True)
    print(f"[{a.case}] memory: {life.recall(sig)} | confidence {res['memory_confidence']} | "
          f"{len(life.store)} rows, {res['memory_bytes']} bytes | sha {life.sha()[:12]}", flush=True)


if __name__ == "__main__":
    main()
