#!/usr/bin/env python3
"""Attack the closed loop. A design is only flawless until someone measures it.

Four attacks, run one at a time on an idle machine, all live:

  1 SWEEP        break the memory at every line a shipped class can touch, in every way that class breaks
                 it, and record what the loop does. The only acceptable outcomes are a byte-exact repair or
                 a refusal. A GREEN-BUT-DIFFERENT memory is the failure this attack is looking for, and a
                 break the memory's own suite cannot see is the other.
  2 BROKEN JUDGE break the memory's SUITE instead of the memory. The suite is trusted absolutely, so this
                 asks whether a corrupted judge can make the system corrupt a memory that was correct.
  3 POISON       teach the head the wrong class and see what it costs and whether it recovers.
  4 DETERMINISM  the same break three times: the same repaired bytes, and the same memory hash.

  PYTHONPATH=<fluidfix>/src python3 attack.py [--only sweep,judge,poison,determinism]
"""
import argparse, io, json, os, re, shutil, subprocess, sys, time, tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))
from closed_loop import DRIVER, SHIPPED, TAUGHT, PY, SRC, sh, suite_green, MEM   # noqa: E402
from life import Life                                                             # noqa: E402

WORK = Path(os.environ.get("TMPDIR", "/tmp")) / "closed-loop-attack"
DICT = str(HERE / "memory_rules.py")


def fresh(tag: str) -> Path:
    w = WORK / tag
    shutil.rmtree(w, ignore_errors=True); w.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(MEM, w)
    return w


def guard(work: Path, rel: str, kind: int, env, dictionary=""):
    """One small fluidfix over one territory and one class, judged by that territory's own suite."""
    p = subprocess.run([PY, "-c", DRIVER, str(SRC), rel, str(kind), dictionary],
                       cwd=work, env=env, capture_output=True, text=True, timeout=600)
    out = p.stdout + p.stderr
    runs = re.search(r"suite_runs=(\d+)", out)
    return p.returncode, int(runs.group(1)) if runs else 0, out


def lake_over(work: Path, rel: str, env, pristine: str, classes, dictionary=""):
    """Every class in turn over one file; returns the first green, whether it is byte-exact, and the cost."""
    runs = 0
    for k in classes:
        clone = work.parent / (work.name + f"_k{k:02d}")
        shutil.rmtree(clone, ignore_errors=True); shutil.copytree(work, clone)
        code, r, _out = guard(clone, rel, k, env, dictionary)
        runs += r
        if code == 0:
            after = (clone / rel).read_text()
            shutil.rmtree(clone, ignore_errors=True)
            return {"winner": k, "byte_exact": after == pristine, "after": after, "suite_runs": runs}
        shutil.rmtree(clone, ignore_errors=True)
    return {"winner": None, "byte_exact": False, "after": None, "suite_runs": runs}


# ---------------------------------------------------------------- 1. the mutation sweep
def mutations(line: str):
    """Every way a shipped class would break this line — the inverse of the classes that repair it."""
    out = []
    for a, b in ((">=", ">"), ("<=", "<"), (" + ", " - "), (" - ", " + "),
                 ("min(", "max("), ("max(", "min("), ("True", "False"), ("False", "True"),
                 (" and ", " or "), (" or ", " and ")):
        if a in line:
            out.append((line.replace(a, b, 1), f"{a.strip()} -> {b.strip()}"))
    for m in re.finditer(r"(?<![\w.])(\d+)(?![\w.])", line):
        n = int(m.group(1))
        out.append((line[:m.start()] + str(n + 1) + line[m.end():], f"{n} -> {n + 1}"))
    return out


def string_lines(src: str) -> set:
    """Lines whose content lies inside a string literal — prose in a docstring is not code, and mutating
    it is a harness artefact, the same mistake the 2026-09-16 bench made with regexes and format specs."""
    out = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.STRING:
                out.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return out


def sweep(env):
    src = (MEM / "dispatch.py").read_text()
    lines = src.split("\n")
    prose = string_lines(src)
    rows = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#") or (i + 1) in prose:
            continue
        for broken_line, how in mutations(line):
            work = fresh(f"sweep{i}_{len(rows)}")
            trial = lines[:]; trial[i] = broken_line
            (work / "dispatch.py").write_text("\n".join(trial))
            if suite_green(work):
                rows.append({"line": i + 1, "code": s[:58], "break": how, "outcome": "INVISIBLE",
                             "note": "the memory's own suite does not catch this", "suite_runs": 0})
                shutil.rmtree(work, ignore_errors=True)
                continue
            r = lake_over(work, "dispatch.py", env, src, SHIPPED + TAUGHT, DICT)
            outcome = ("byte-exact" if r["byte_exact"] else "WRONG-GREEN" if r["winner"] is not None
                       else "refused")
            rows.append({"line": i + 1, "code": s[:58], "break": how, "outcome": outcome,
                         "winner_class": r["winner"], "suite_runs": r["suite_runs"],
                         "shipped": None if r["byte_exact"] or r["winner"] is None
                         else (r["after"].split("\n")[i].strip()[:70])})
            shutil.rmtree(work, ignore_errors=True)
            print(f"  line {i+1:>3} {s[:44]:46} {how:14} -> {outcome}", flush=True)
    return rows


# ---------------------------------------------------------------- 2. the judge itself is broken
def broken_judge(env):
    """The suite is the only thing that may accept a repair. So: corrupt the suite, leave the memory
    correct, and see whether the loop rewrites a correct memory to satisfy a lie."""
    work = fresh("judge")
    src = (MEM / "dispatch.py").read_text()
    t = (work / "test_dispatch.py").read_text()
    bad = t.replace("assert confident(0.5) is True", "assert confident(0.5) is False", 1)
    assert bad != t
    (work / "test_dispatch.py").write_text(bad)
    red = not suite_green(work)
    r = lake_over(work, "dispatch.py", env, src, SHIPPED + TAUGHT, DICT)
    after = (r["after"] or src)
    verdict = ("refused — a correct memory was left alone" if r["winner"] is None else
               "REWROTE A CORRECT MEMORY to satisfy the corrupted suite")
    changed = [f"{i+1}: {a.strip()} -> {b.strip()}"
               for i, (a, b) in enumerate(zip(src.split("\n"), after.split("\n"))) if a != b]
    shutil.rmtree(work, ignore_errors=True)
    print(f"  suite corrupted, memory correct -> {verdict}", flush=True)
    return {"suite_red": red, "winner_class": r["winner"], "verdict": verdict,
            "lines_changed_in_the_memory": changed, "suite_runs": r["suite_runs"]}


# ---------------------------------------------------------------- 3. poison the head's memory
def poison(env):
    """Teach the head a class that cannot repair anything here, then break the memory for real."""
    db = HERE / "attack_head_memory.json"
    db.unlink(missing_ok=True)
    life = Life(str(db))
    life.learn("repairs-a-memory", "kind:12")          # a lie: flipped-boolean repairs nothing here
    life.save()
    work = fresh("poison")
    src = (MEM / "dispatch.py").read_text()
    (work / "dispatch.py").write_text(src.replace("    return conf >= THRESH", "    return conf > THRESH", 1))
    assert not suite_green(work)
    wasted = lake_over(work, "dispatch.py", env, src, [12], DICT)          # wave 1: the poisoned class
    widened = lake_over(work, "dispatch.py", env, src, [k for k in SHIPPED + TAUGHT if k != 12], DICT)
    if widened["winner"] is not None and widened["byte_exact"]:
        life.learn("repairs-a-memory", f"kind:{widened['winner']}"); life.save()
    recovered = life.recall("repairs-a-memory")
    shutil.rmtree(work, ignore_errors=True)
    print(f"  poisoned wave 1 cost {wasted['suite_runs']} suite runs, then widened and repaired "
          f"(byte-exact {widened['byte_exact']}); memory now recalls {recovered}", flush=True)
    return {"poisoned_with": "kind:12", "wave1_wasted_runs": wasted["suite_runs"],
            "wave1_repaired": wasted["winner"] is not None, "widened_winner": widened["winner"],
            "byte_exact_after_widening": widened["byte_exact"], "recall_after": recovered,
            "history": [v for v, _c in life.history("repairs-a-memory")]}


# ---------------------------------------------------------------- 4. determinism
def determinism(env):
    src = (MEM / "dispatch.py").read_text()
    seen = []
    for i in range(3):
        work = fresh(f"det{i}")
        (work / "dispatch.py").write_text(src.replace("    return conf >= THRESH", "    return conf > THRESH", 1))
        r = lake_over(work, "dispatch.py", env, src, SHIPPED, "")
        db = WORK / f"life{i}.json"; db.unlink(missing_ok=True)
        life = Life(str(db)); life.learn("repairs-a-memory", f"kind:{r['winner']}"); life.save()
        seen.append({"winner": r["winner"], "byte_exact": r["byte_exact"], "suite_runs": r["suite_runs"],
                     "life_sha": life.sha()})
        shutil.rmtree(work, ignore_errors=True)
    same = len({(x["winner"], x["byte_exact"], x["life_sha"]) for x in seen}) == 1
    print(f"  three identical breaks -> same winner, bytes and memory hash: {same}", flush=True)
    return {"runs": seen, "identical": same}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default="sweep,judge,poison,determinism")
    a = ap.parse_args()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    want = a.only.split(",")
    out, t0 = {}, time.time()
    if "sweep" in want:
        print("ATTACK 1 — mutation sweep over the memory"); out["sweep"] = sweep(env)
    if "judge" in want:
        print("ATTACK 2 — the judge itself is broken"); out["broken_judge"] = broken_judge(env)
    if "poison" in want:
        print("ATTACK 3 — poison the head's memory"); out["poison"] = poison(env)
    if "determinism" in want:
        print("ATTACK 4 — determinism"); out["determinism"] = determinism(env)
    out["seconds"] = round(time.time() - t0, 1)
    if "sweep" in out:
        s = out["sweep"]
        out["sweep_tally"] = {"cases": len(s),
                              "byte_exact": sum(r["outcome"] == "byte-exact" for r in s),
                              "wrong_green": sum(r["outcome"] == "WRONG-GREEN" for r in s),
                              "refused": sum(r["outcome"] == "refused" for r in s),
                              "invisible_to_the_suite": sum(r["outcome"] == "INVISIBLE" for r in s)}
        print("\nSWEEP:", json.dumps(out["sweep_tally"]))
    (HERE / "attack_results.json").write_text(json.dumps(out, indent=1))
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"\nATTACKS_DONE in {out['seconds']}s")


if __name__ == "__main__":
    main()
