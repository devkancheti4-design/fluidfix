#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The loop that starts as one fluidfix and GROWS as a net — including downward, on a ruling.

`net.py` grows a search across a repository and its law returns two directions, both of which search CODE:

    REFUTED   not in this territory        -> WIDER
    CAPPED    here, but unproven           -> DEEPER

`closed_loop.py` shows the third direction — the head's Life is not a table but a FILE (`memory/dispatch.py`)
with its own suite, so a fluidfix can repair the memory the way it repairs code. But there it descends
because a human passed `--break gate`. Nothing in the law ever says *go down*, so the two grow apart.

There is a ruling that says it, and it needs no hand:

    MISDIRECTED   the memory REMEMBERED the answering class and wave 1 still did not carry it
                  -> DOWN: the memory file becomes the territory, and its suite becomes the judge

That is a pure memory fault, decidable against the memory's own record and never against ground truth about
the code. Wider and deeper cannot help: both search a repository that was never the problem.

And it arrives on its own. `WAVE1_CLASSES = 2` is correct for two remembered classes and becomes wrong the
moment a third is learned and an old one answers. Nothing is broken by hand here; the memory is simply
outgrown, which is what growth means.

One more thing has to be true for the descent to work at all, and it is the whole shape of the loop: when
MISDIRECTED fires the memory's suite is still GREEN — it passes every incident it has seen. So the descent
must first WRITE THE INCIDENT INTO THE SUITE. That is what turns the memory red, and only then can a
fluidfix repair it, judged by a test that now encodes the very failure that triggered the descent.

Incidents are the recorded ones from ../llm-fusion-2026-09-16/cases (four repositories, seven classes).

  PYTHONPATH=<fluidfix>/src python3 grown_loop.py [--cold] [--wave1-cap N]
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
MEM = HERE / "memory"
CASES = HERE.parent / "llm-fusion-2026-09-16" / "cases"
MEM_RULES = HERE / "memory_rules.py"      # taught at the MEMORY's own level
PY = str(HERE.parents[1] / ".venv" / "bin" / "python")
sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))
from life import Life                                                     # noqa: E402

# the recorded corpus tags a class on every case; these are fluidfix's own numbers for them
CLS = {"lit": 1, "add": 3, "cmp": 10, "andor": 4, "getdef": 5, "notdrop": 6, "lenm1": 7}
SHIPPED = [0, 1, 2, 3, 8, 9, 10, 11, 12]
TAUGHT = [4, 5, 6, 7]       # the slots memory_rules.py may claim at this level

sys.path.insert(0, str(HERE))
from closed_loop import DRIVER, sh, suite_green                           # noqa: E402


def incidents():
    """Every recorded real-repo case, as (repo, id, territory, class). The order is the order they arrive."""
    out = []
    for m in sorted(CASES.glob("*/*/mutation.json")):
        d = json.load(open(m))
        c = CLS.get(d.get("cls"))
        if c is None:
            continue
        out.append({"repo": m.parts[-3], "id": m.parts[-2], "rel": d["file"], "kind": c})
    return out


def survey_for(repo, allc):
    """What a survey of that repository would say: which territories can exhibit which classes.

    Built from the recorded corpus rather than invented -- every (file, class) pair here is one some case
    in that repository actually exhibited."""
    s = {}
    for i in allc:
        if i["repo"] == repo:
            s.setdefault(i["rel"], set()).add(i["kind"])
    return [(rel, sorted(k)) for rel, k in sorted(s.items())]


def load_dispatch(work: Path):
    sys.path.insert(0, str(work))
    for m in ("dispatch",):
        sys.modules.pop(m, None)
    import dispatch                                                        # noqa: E402
    sys.path.remove(str(work))
    return dispatch


TEST_TEMPLATE = '''

# --- appended by the loop: the incident that misdirected wave 1. The memory is red until it carries this.
{name} = ({survey!r}, {remembered!r}, {answer!r})


def test_{fn}():
    survey, remembered, answer = {name}
    assert answer in wave1(survey, remembered)
'''


def descend(work: Path, incident, survey, remembered, life, env, depth=1):
    """DOWN: write the incident into the memory's suite, then let a fluidfix repair the memory."""
    tag = f"{incident['repo']}_{incident['id']}".replace("-", "_").replace(".", "_")
    t = work / "test_dispatch.py"
    t.write_text(t.read_text() + TEST_TEMPLATE.format(
        name=tag.upper(), fn=tag, survey=survey, remembered=remembered,
        answer=(incident["rel"], incident["kind"])))
    if suite_green(work):
        return {"repaired": False, "why": "the incident did not turn the memory's suite red", "tried": 0}

    # the lake inside the memory: its head remembers which class repairs a memory
    mem_remembered = [int(v.split(":")[1]) for v, _c in reversed(life.history("repairs-a-memory"))
                      if v.startswith("kind:")]
    # every class this level has: shipped, plus whatever is taught at the memory's own level.
    # Trying only the shipped ones would make the refusal an artefact of the harness.
    have = SHIPPED + TAUGHT
    order = mem_remembered + [k for k in have if k not in mem_remembered]
    for n, kind in enumerate(order, 1):
        r = sh([PY, "-c", DRIVER, str(SRC), "dispatch.py", str(kind), str(MEM_RULES)],
               cwd=work, env=env, timeout=300)
        if r.returncode == 0:
            life.learn("repairs-a-memory", f"kind:{kind}"); life.save()
            return {"repaired": True, "kind": kind, "tried": n,
                    "wave1_was": len(mem_remembered), "depth": depth}
    return {"repaired": False, "why": "no shipped class repairs this memory", "tried": len(order)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cold", action="store_true"); ap.add_argument("--work", default=None)
    a = ap.parse_args()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    head_mem = HERE / "grown_head_memory.json"
    if a.cold:
        head_mem.unlink(missing_ok=True)
    work = Path(a.work) if a.work else Path(os.environ.get("TMPDIR", "/tmp")) / "grown-loop-memory"
    shutil.rmtree(work, ignore_errors=True); shutil.copytree(MEM, work)
    sh(["git", "init", "-q", "-b", "main"], cwd=work); sh(["git", "add", "-A"], cwd=work)
    sh(["git", "-c", "user.name=loop", "-c", "user.email=l@f", "commit", "-qm", "memory"], cwd=work)
    assert suite_green(work), "the memory does not start correct"

    head_life = Life(str(head_mem))
    lake_life = Life(str(work / "_lake_memory.json"))
    allc = incidents()
    print(f"{len(allc)} recorded incidents over {len({i['repo'] for i in allc})} repositories, "
          f"{len({i['kind'] for i in allc})} classes. The memory starts correct and is never broken by hand.\n")
    print(f"{'#':>3} {'incident':28} {'class':>6} {'ruling':>13}  what the net did")

    rows, t0 = [], time.time()
    for n, inc in enumerate(allc, 1):
        dispatch = load_dispatch(work)
        remembered = [int(v.split(":")[1]) for v, _c in reversed(lake_life.history("shapes"))
                      if v.startswith("kind:")]
        survey = survey_for(inc["repo"], allc)
        w1 = dispatch.wave1(survey, remembered)
        answer = (inc["rel"], inc["kind"])
        row = {"n": n, "incident": f"{inc['repo']}/{inc['id']}", "kind": inc["kind"],
               "remembered": list(remembered), "wave1": len(w1)}

        if answer in w1:
            row["ruling"] = "HIT"
            row["cost"] = len(w1)
            note = f"wave 1 carried it ({len(w1)} fluidfix{'' if len(w1) == 1 else 'es'})"
        elif inc["kind"] not in remembered:
            row["ruling"] = "WIDER"
            row["cost"] = len(dispatch.wave2(survey, remembered, w1)) + len(w1)
            note = f"class unseen -> widen to wave 2 ({row['cost']} fluidfixes), then learn it"
        else:
            row["ruling"] = "MISDIRECTED"
            note = "it KNEW this class and wave 1 dropped it -> DOWN into the memory"
            print(f"{n:>3} {row['incident']:28} {inc['kind']:>6} {row['ruling']:>13}  {note}", flush=True)
            got = descend(work, inc, survey, remembered, head_life, env)
            row["descent"] = got
            if got["repaired"]:
                sh(["git", "-c", "user.name=loop", "-c", "user.email=l@f", "commit", "-qam",
                    f"memory grown at {inc['repo']}/{inc['id']}"], cwd=work)
                dispatch = load_dispatch(work)
                w1b = dispatch.wave1(survey, remembered)
                row["carried_after"] = answer in w1b
                print(f"{'':>3} {'':28} {'':>6} {'':>13}  repaired by class {got['kind']} after "
                      f"{got['tried']} tried; wave 1 {len(w1)} -> {len(w1b)}; "
                      f"carries the answer now: {row['carried_after']}", flush=True)
            else:
                print(f"{'':>3} {'':28} {'':>6} {'':>13}  REFUSED: {got['why']} "
                      f"(memory rolled back byte-exact)", flush=True)
            rows.append(row)
            lake_life.learn("shapes", f"kind:{inc['kind']}"); lake_life.save()
            continue

        print(f"{n:>3} {row['incident']:28} {inc['kind']:>6} {row['ruling']:>13}  {note}", flush=True)
        rows.append(row)
        lake_life.learn("shapes", f"kind:{inc['kind']}"); lake_life.save()

    from collections import Counter
    tally = Counter(r["ruling"] for r in rows)
    desc = [r for r in rows if r.get("descent")]
    ok = [r for r in desc if r["descent"]["repaired"]]
    (HERE / "grown_loop.json").write_text(json.dumps({"rows": rows, "tally": dict(tally)}, indent=2))
    print(f"\nrulings: " + ", ".join(f"{k} {v}" for k, v in tally.most_common()))
    print(f"descents: {len(desc)}, memory repaired by a fluidfix in {len(ok)}; "
          f"classes tried per descent: {[r['descent']['tried'] for r in desc]}")
    print(f"the head's memory of what repairs a memory: {json.load(open(head_mem)) if head_mem.exists() else '{}'}")
    print(f"{round(time.time() - t0, 1)}s  GROWN_LOOP_DONE")


if __name__ == "__main__":
    main()
