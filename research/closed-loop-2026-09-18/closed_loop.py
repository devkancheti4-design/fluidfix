#!/usr/bin/env python3
"""The loop closed: every lake is headed by one fluidfix, and every head's memory is itself a lake.

    a lake            N small fluidfixes over territories, moored to ONE head fluidfix
    the head's Life   not a table — a FILE of dispatch rules (memory/dispatch.py)
    that file         is the territory of the next lake down, judged by its own suite
                      (memory/test_dispatch.py: every incident the lake has already answered, replayed)
    its head          one fluidfix, with its own memory of which class repairs a memory
    the fixed point   that memory is a single row, its lake is a single fluidfix, and head, lake and
                      memory are the same object — the loop closes and descends no further

So when the memory is wrong, nothing outside the system fixes it: a fluidfix repairs the memory the way a
fluidfix repairs code, with the memory's own tests as the judge and byte-exact rollback on rejection.

This driver breaks the memory at its gate — the boundary the judge is built on — and lets the loop run.

  PYTHONPATH=<fluidfix>/src python3 closed_loop.py [--break gate|cap]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
MEM = HERE / "memory"
PY = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))
from life import Life                                                     # noqa: E402

# the two ways this memory can be wrong, both inside fluidfix's shipped vocabulary
BREAKS = {
    "gate": ("    return conf >= THRESH", "    return conf > THRESH",
             "the gate stops answering at exactly its own threshold (a strictness slip)"),
    "cap":  ("WAVE1_CLASSES = 2", "WAVE1_CLASSES = 1",
             "wave 1 carries one class fewer than it should (an off-by-one in the cap)"),
}

# one small fluidfix: one territory, one class, full sight, the territory's own suite as judge
DRIVER = """
import sys
src, rel, kind, dictionary = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import KINDS, load_dictionary
if dictionary:
    load_dictionary(dictionary)
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
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
print(f"routed: kind {kind} ({KINDS[kind][0]}) x {rel}: {len(mine)} observations", flush=True)
if not mine:
    print("refused: this territory cannot exhibit this class"); raise SystemExit(2)
res = repair(o, rel, mine)
print(f"suite_runs={res.suite_runs}")
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""

SHIPPED = [0, 1, 2, 3, 8, 9, 10, 11, 12]          # the classes fluidfix ships with
TAUGHT = [4, 5, 6, 7]                             # the slots a dictionary may claim


def sh(cmd, cwd=None, env=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def suite_green(work: Path) -> bool:
    return sh([PY, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"], cwd=work).returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--break", dest="brk", default="gate", choices=list(BREAKS))
    ap.add_argument("--work", default=None)
    ap.add_argument("--dictionary", default=None, help="a class taught at the memory's own level")
    a = ap.parse_args()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    work = Path(a.work) if a.work else Path(os.environ.get("TMPDIR", "/tmp")) / "closed-loop-memory"
    shutil.rmtree(work, ignore_errors=True); shutil.copytree(MEM, work)
    sh(["git", "init", "-q", "-b", "main"], cwd=work); sh(["git", "add", "-A"], cwd=work)
    sh(["git", "-c", "user.name=loop", "-c", "user.email=loop@fluidfix", "commit", "-qm", "memory, correct"], cwd=work)

    pristine, broken, why = BREAKS[a.brk]
    print("LEVEL 0 — a lake of small fluidfixes over a repository, headed by one fluidfix.")
    print("          The head asks its Life where to dispatch. Recorded: with the shape remembered, the")
    print("          arrow incident cost 1 fluidfix and 2 suite runs (research/lake-2026-09-18).")
    print()
    print(f"LEVEL 1 — the head's Life is not a table: it is {MEM.name}/dispatch.py, with its own suite.")
    print(f"          Breaking it: {why}")
    src_file = work / "dispatch.py"
    text = src_file.read_text()
    assert text.count(pristine) == 1, "the memory has drifted from what this driver knows how to break"
    src_file.write_text(text.replace(pristine, broken, 1))
    sh(["git", "-c", "user.name=loop", "-c", "user.email=loop@fluidfix", "commit", "-qam", "memory, broken"], cwd=work)
    assert not suite_green(work), "the memory's own suite does not catch this break"
    print("          the memory's own suite is RED — the Life knows it is wrong", flush=True)
    print()

    # ---- the lake inside the memory: one fluidfix per class over the memory's one territory
    life = Life(str(HERE / "head_memory.json"))
    remembered = [int(v.split(":")[1]) for v, _c in reversed(life.history("repairs-a-memory"))
                  if v.startswith("kind:")]
    wave1 = remembered[:1]
    print(f"LEVEL 2 — the lake INSIDE that Life. Its head remembers {remembered or 'nothing'}, so wave 1 is "
          f"{len(wave1) or len(SHIPPED)} fluidfix{'' if len(wave1) == 1 else 'es'} over dispatch.py.", flush=True)

    t0 = time.time()
    winner, guards, waves = None, {}, []
    DICT[0] = a.dictionary or ""
    classes = SHIPPED + (TAUGHT if a.dictionary else [])
    for wave, plan in enumerate([wave1, [k for k in classes if k not in wave1]], start=1):
        if not plan or winner is not None:
            continue
        if wave == 2 and wave1:
            print("            wave 1 refused — widening to every class, no coverage lost", flush=True)
        winner, wg = run_wave(plan, work, env, text)
        guards.update(wg); waves.append(len(plan))
    runs_total = sum(g["suite_runs"] for g in guards.values())
    wall = round(time.time() - t0, 1)

    for k, g in sorted(guards.items()):
        mark = "REPAIRED, byte-exact" if g["byte_exact"] and g["exit"] == 0 else (
               "green but not the original bytes" if g["exit"] == 0 else "refused")
        print(f"            kind {k:2}  {mark:32} {g['suite_runs']:>3} suite runs  {g['seconds']:>5.1f}s")

    if winner is not None:
        life.learn("repairs-a-memory", f"kind:{winner}")
        life.save()
    print()
    print(f"LEVEL 3 — the fixed point. That head's own memory is now {len(life.store)} row(s), "
          f"{len(life.dumps().encode())} bytes: {[v for v, _ in life.history('repairs-a-memory')]}.")
    print("          Its lake is one fluidfix over one row, and its head is that same fluidfix — head,")
    print("          lake and memory are one object, so the loop closes and descends no further.")
    print()
    print(f"RESULT    the memory repaired itself: class {winner}, {sum(waves)} fluidfixes dispatched, "
          f"{runs_total} suite runs, {wall}s, 0 tokens.")

    res = {"broke": a.brk, "why": why, "waves": waves, "dispatched": sum(waves), "remembered_before": remembered,
           "winner_kind": winner, "byte_exact": bool(winner is not None), "suite_runs": runs_total,
           "wall_s": wall, "tokens": 0, "head_memory_rows": len(life.store),
           "head_memory_bytes": len(life.dumps().encode()), "guards": guards}
    (HERE / f"closed_loop_{a.brk}_{'warm' if remembered else 'cold'}.json").write_text(json.dumps(res, indent=1))
    shutil.rmtree(work, ignore_errors=True)


DICT = [""]


def run_wave(plan, work, env, pristine_text):
    """One wave of the memory's own lake: a fluidfix per class, over the memory file, judged by its suite."""
    procs = {}
    for k in plan:
        clone = work.parent / f"{work.name}_k{k:02d}"
        shutil.rmtree(clone, ignore_errors=True); shutil.copytree(work, clone)
        procs[k] = (clone, time.time(), subprocess.Popen([PY, "-c", DRIVER, str(SRC), "dispatch.py", str(k), DICT[0]],
                    cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    winner, guards = None, {}
    for k, (clone, ts, pr) in procs.items():
        out, _ = pr.communicate(timeout=600)
        runs = re.search(r"suite_runs=(\d+)", out or "")
        fixed = (clone / "dispatch.py").read_text() == pristine_text
        guards[k] = {"exit": pr.returncode, "seconds": round(time.time() - ts, 1),
                     "suite_runs": int(runs.group(1)) if runs else 0, "byte_exact": fixed}
        if pr.returncode == 0 and fixed and winner is None:
            winner = k
        shutil.rmtree(clone, ignore_errors=True)
    return winner, guards


if __name__ == "__main__":
    main()
