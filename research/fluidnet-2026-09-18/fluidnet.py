#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""fluidnet — the organs fused: one net that searches, certifies, descends into its own memory, and learns.

Everything measured separately today is one mechanism, and this runs it as one. A single incident enters,
and every organ that touches it is the same organ at a different scale:

  SURVEY      which territories can exhibit which classes — the address space, read off the code
  DISPATCH    the memory (research/closed-loop-2026-09-18/memory/dispatch.py) says what wave 1 carries
  GROW        one small fluidfix per node, and the node's RULING decides what the net spawns next:
                REFUTED      not here            -> WIDER    the next class here, this class elsewhere
                MISDIRECTED  the memory knew the answering class and wave 1 dropped it
                                                 -> DOWN     the memory file becomes the territory, the
                                                             incident becomes a test, a fluidfix repairs it
  CERTIFY     a green is not a repair. Red before, green on the FULL suite, stable on re-check, nothing
              else broken, byte-exact rollback otherwise (research/certify-2026-09-18)
  WITNESS     two different programs that both pass -> AMB. The net grows over INPUT space until it finds
              the input that separates them: the place the specification never decided
              (research/model-divergence-2026-09-18)
  LEARN       the class that answered -> the lake's memory; the class that repaired a memory -> the head's;
              and a fault no class reaches is a demand for a taught class, which is the only step a human
              still takes

The territories are real modules with real tests, the fault is a real mutation from the shipped vocabulary,
and nothing is judged by anything but the suite.

  PYTHONPATH=<fluidfix>/src python3 fluidnet.py [--cold] [--territories 8]
"""
from __future__ import annotations

import argparse, ast, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
LOOP = HERE.parent / "closed-loop-2026-09-18"
DIVERGE = HERE.parent / "model-divergence-2026-09-18"
CERT = HERE.parent / "certify-2026-09-18"
BUGS = HERE.parent / "model-bugs-2026-09-18"
PY = str(HERE.parents[1] / ".venv" / "bin" / "python")

sys.path.insert(0, str(SRC)); sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))
sys.path.insert(0, str(LOOP)); sys.path.insert(0, str(CERT)); sys.path.insert(0, str(DIVERGE))

from fluidfix.acts import KINDS                                            # noqa: E402
from fluidfix.oracle import Oracle                                         # noqa: E402
from life import Life                                                      # noqa: E402
from closed_loop import DRIVER, sh, suite_green as _raw_green             # noqa: E402


def suite_green(root) -> bool:
    """Judge through the Oracle, never through a bare pytest call.

    A same-size rewrite -- `<` for `>` is the canonical one -- keeps the file's size identical, and CPython
    validates a .pyc on whole-second mtime PLUS size. Two writes inside one second therefore re-import the
    STALE bytecode, and the mutation looks like it never happened. oracle.py carries this scar already
    (-B, PYTHONDONTWRITEBYTECODE, __pycache__ clearing); calling pytest directly threw all of it away, and
    this file's first warm run duly reported that a planted fault had not turned the suite red.
    """
    return Oracle(str(root), python=PY).green()
import grown_loop as GL                                                    # noqa: E402

WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/fluidnet")
SHIPPED = [0, 1, 2, 3, 8, 9, 10, 11, 12]

# one real fault from the shipped vocabulary, applied to a real line
MUTATIONS = [
    (10, re.compile(r"(?<![-<>=!])<(?![<>=])"), ">", "flipped-comparison-direction"),
    (3,  re.compile(r"\s\+\s"), " - ", "flipped-additive"),
    (12, re.compile(r"\bTrue\b"), "False", "flipped-boolean"),
    (9,  re.compile(r"\+=(?!=)"), "-=", "flipped-augmented-assign"),
    (0,  re.compile(r"(?<![<>=!])>=(?!=)"), ">", "strictness"),
]


# ------------------------------------------------------------------ the territories
def build_world(root: Path, mods: list[tuple[str, str, list[str]]]) -> None:
    """A package of real modules, each with its own tests. The suite is the only judge from here on."""
    shutil.rmtree(root, ignore_errors=True)
    (root / "pkg").mkdir(parents=True); (root / "tests").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    for name, code, tests in mods:
        (root / "pkg" / f"{name}.py").write_text(code if code.endswith("\n") else code + "\n")
        body = [f"from pkg.{name} import {name}", ""]
        for i, a in enumerate(tests):
            body += [f"def test_{name}_{i}():", f"    {a}", ""]
        (root / "tests" / f"test_{name}.py").write_text("\n".join(body))
    (root / "conftest.py").write_text("import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\n")


def survey(root: Path) -> list[tuple[str, list[int]]]:
    """Which territories can exhibit which classes — fluidfix's own signals, read off the code."""
    out = []
    for p in sorted((root / "pkg").glob("*.py")):
        if p.name == "__init__.py":
            continue
        text = p.read_text()
        kinds = sorted(k for k, v in KINDS.items()
                       if v[2] is not None and any(v[2].search(l) for l in text.split("\n")
                                                   if l.strip() and not l.strip().startswith(('"', "#"))))
        out.append((f"pkg/{p.name}", [k for k in kinds if k in SHIPPED]))
    return out


def break_one(root: Path, target: str, only: int | None = None) -> dict | None:
    """Apply one real mutation from the vocabulary; return what was done, for the byte-exact check."""
    p = root / target
    lines = p.read_text().split("\n")
    # `if only` would be False for class 0 — the zero-is-falsy slip, which silently planted the
    # wrong class and made a forced run look like an ordinary one.
    for kind, pat, rep, name in ([m for m in MUTATIONS if m[0] == only]
                                 if only is not None else MUTATIONS):
        for i, l in enumerate(lines):
            if not l.strip() or l.strip().startswith(('"', "#")) or "def " in l:
                continue
            if pat.search(l):
                orig = l
                lines[i] = pat.sub(rep, l, count=1)
                p.write_text("\n".join(lines))
                return {"file": target, "lineno": i + 1, "orig": orig, "kind": kind, "name": name}
    return None


# ------------------------------------------------------------------ one node of the net
def node(root: Path, rel: str, kind: int, env) -> tuple[int, str]:
    r = sh([PY, "-c", DRIVER, str(SRC), rel, str(kind), ""], cwd=root, env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def certify(root: Path, rel: str, original: str, confirm: int = 2) -> dict:
    """A green is not a repair. The certificate, on the repository the net just changed."""
    import hashlib
    o = Oracle(str(root), python=PY)
    f = root / rel
    patched = f.read_text()
    ok, why = o.check()
    runs = 1
    if not ok:
        f.write_text(original)
        return {"certified": False, "why": why[:140], "suite_runs": runs, "rolled_back": True}
    for i in range(confirm):
        again, why2 = o.check(); runs += 1
        if not again:
            f.write_text(original)
            return {"certified": False, "why": f"green once, red on re-check {i+1}: {why2[:100]}",
                    "suite_runs": runs, "rolled_back": True}
    return {"certified": True, "why": "red before, green on the full suite, stable on re-check",
            "suite_runs": runs, "sha": hashlib.sha256(patched.encode()).hexdigest()[:12]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cold", action="store_true"); ap.add_argument("--territories", type=int, default=8)
    ap.add_argument("--target", default=None, help="which module to break (default: the last territory)")
    ap.add_argument("--kind", type=int, default=None, help="force which class of fault to plant")
    a = ap.parse_args()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    WORK.mkdir(parents=True, exist_ok=True)
    lake_mem = HERE / "lake_memory.json"; head_mem = HERE / "head_memory.json"
    if a.cold:
        lake_mem.unlink(missing_ok=True); head_mem.unlink(missing_ok=True)

    # ---- the world: real modules, real tests
    rows = (json.load(open(BUGS / "written_haiku-hard.json"))["rows"]
            + json.load(open(BUGS / "written_haiku.json"))["rows"])
    mods = [(r["name"], r["code"], r["tests"]) for r in rows if r["passed"]][: a.territories]
    root = WORK / "world"
    build_world(root, mods)
    assert suite_green(root), "the world does not start green"

    # ---- the memory: the repaired dispatch policy, as a file, with its own suite
    mem = WORK / "memory"
    shutil.rmtree(mem, ignore_errors=True); shutil.copytree(LOOP / "memory", mem)
    sh(["git", "init", "-q", "-b", "main"], cwd=mem); sh(["git", "add", "-A"], cwd=mem)
    sh(["git", "-c", "user.name=n", "-c", "user.email=n@f", "commit", "-qm", "memory"], cwd=mem)

    sv = survey(root)
    target = a.target or sv[-1][0]
    mut = break_one(root, target, a.kind)
    if not mut:
        for rel, _k in sv:                       # that class has no site here; take the first that does
            mut = break_one(root, rel, a.kind)
            if mut:
                target = rel
                break
    assert mut, "no mutation site found for that class"
    original = None
    print(f"world: {len(sv)} territories, {sum(len(k) for _r, k in sv)} (territory, class) pairs")
    print(f"fault: {mut['name']} (class {mut['kind']}) planted in {mut['file']}:{mut['lineno']}")
    assert not suite_green(root), "the fault did not turn the suite red"
    original = "\n".join(
        (root / mut["file"]).read_text().split("\n")[:mut["lineno"] - 1]
        + [mut["orig"]] + (root / mut["file"]).read_text().split("\n")[mut["lineno"]:])
    print()

    lake, head = Life(str(lake_mem)), Life(str(head_mem))
    remembered = [int(v.split(":")[1]) for v, _c in reversed(lake.history("shapes")) if v.startswith("kind:")]
    sys.path.insert(0, str(mem)); sys.modules.pop("dispatch", None)
    import dispatch                                                        # noqa: E402
    sys.path.remove(str(mem))
    w1 = dispatch.wave1(sv, remembered)
    answer = (mut["file"], mut["kind"])
    print(f"DISPATCH  memory knows {remembered or 'nothing'} -> wave 1 is {len(w1)} node(s)")

    report = {"territories": len(sv), "pairs": sum(len(k) for _r, k in sv), "fault": mut,
              "remembered": remembered, "wave1": len(w1), "nodes": [], "descent": None}

    # ---- MISDIRECTED: the memory knew this class and did not carry it -> DOWN, before searching the code
    if mut["kind"] in remembered and answer not in w1:
        print("RULING    MISDIRECTED — it knew this class and wave 1 dropped it -> DOWN into the memory")
        got = GL.descend(mem, {"repo": "fluidnet", "id": "live", "rel": mut["file"], "kind": mut["kind"]},
                         sv, remembered, head, env)
        report["descent"] = got
        print(f"          {'repaired by class ' + str(got['kind']) if got['repaired'] else 'REFUSED: ' + got['why']}"
              f" after {got['tried']} tried")
        if got["repaired"]:
            sys.path.insert(0, str(mem)); sys.modules.pop("dispatch", None)
            import dispatch as d2                                          # noqa: E402
            sys.path.remove(str(mem))
            w1 = d2.wave1(sv, remembered)
            print(f"          wave 1 now {len(w1)} node(s); carries the answer: {answer in w1}")

    # ---- GROW: wave 1 first, then wider by refusal
    order = [n for n in w1] + [(rel, k) for rel, ks in sv for k in ks if (rel, k) not in w1]
    t0, green = time.time(), None
    for i, (rel, k) in enumerate(order, 1):
        rc, out = node(root, rel, k, env)
        ruling = "SHIP" if rc == 0 else ("EMPTY" if "cannot exhibit" in out else "REFUTED")
        report["nodes"].append({"rel": rel, "kind": k, "ruling": ruling})
        if rc == 0:
            green = (rel, k)
            print(f"GROW      node {i}: {rel} class {k} -> SHIP (the first green stops the net)")
            break
        if i <= 6 or ruling == "SHIP":
            print(f"GROW      node {i}: {rel} class {k} -> {ruling}"
                  f"{'  (wider)' if ruling != 'SHIP' else ''}")
    print(f"          {len(report['nodes'])} nodes of {report['pairs']} possible, "
          f"{round(time.time() - t0, 1)}s")

    # ---- CERTIFY: a green is not a repair
    if green:
        cert = certify(root, green[0], original)
        report["certificate"] = cert
        print(f"CERTIFY   {'CERTIFIED' if cert['certified'] else 'REFUSED'} — {cert['why']} "
              f"({cert['suite_runs']} suite runs)")
        if cert["certified"]:
            back = (root / green[0]).read_text().split("\n")[mut["lineno"] - 1]
            report["byte_exact"] = back == mut["orig"]
            print(f"          restored the original line byte-for-byte: {report['byte_exact']}")
            lake.learn("shapes", f"kind:{green[1]}"); lake.save()
            print(f"LEARN     the lake remembers kind:{green[1]}; "
                  f"the head remembers {dict(json.load(open(head_mem)))['repairs-a-memory'] if head_mem.exists() and 'repairs-a-memory' in json.load(open(head_mem)) else 'nothing yet'}")
    else:
        print("CERTIFY   nothing to certify — the net found no green")

    (HERE / f"fluidnet_{'cold' if a.cold else 'warm'}.json").write_text(json.dumps(report, indent=1))
    print("FLUIDNET_DONE")


if __name__ == "__main__":
    main()
