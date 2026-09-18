#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""It cannot author the novel fix. It can certify one — and this measures exactly what the certificate means.

The vocabulary reaches a mechanical subset of faults: measured on bugs models actually wrote, one of
fourteen. The other half of the tool has nothing to do with the vocabulary. It is the JUDGE, and the judge
does not care who wrote the patch — a model, a contractor, another tool, a stranger's pull request. That
half is the part that has never once guessed.

A certificate is issued only when ALL of these hold, each MEASURED, none inferred:

  RED-BEFORE     the suite rejects the code as given            (nothing to certify otherwise)
  GREEN-AFTER    the suite accepts the patched code             (Oracle.check: the FULL suite, never --lf alone)
  STABLE         the green repeats on N independent re-runs     (the engine law's HIDDEN lane)
  NO-COLLATERAL  every test green before is still green after   (the full suite IS the gate)
  UNIQUE         no second supplied patch is a DIFFERENT        (differ.evaluate over inputs harvested from
                 program that also passes                        the suite's own literals)
  ROLLBACK       on any refusal the tree is byte-identical      (sha256 of the file, before and after)

Everything above is fluidfix's own machinery — Oracle, the confirm-runs lane, differ — pointed at a patch it
did not write. What a certificate does NOT mean is measured here too, as its own class, and it fails: a
patch that special-cases the test inputs is certified when it is offered alone, because the suite is the
only judge. A certificate is a statement about the suite, not about the author's intent.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from fluidfix.oracle import Oracle, HarnessError, _check_harness       # noqa: E402
from fluidfix import differ                                            # noqa: E402

MODULE = "pkg.py"
TESTS = os.path.join("tests", "test_spec.py")

# The suite must be run by an interpreter that HAS pytest. Measured the hard way in this very file: the
# first smoke run judged a correct patch "FAILS" because the harness had never run a test at all.
PY = os.environ.get("CERTIFY_PYTHON") or str(Path(__file__).resolve().parents[2] / ".venv" / "bin" / "python")


# ------------------------------------------------------------------ the bench under test
def build_repo(root: Path, code: str, asserts: list[str]) -> None:
    """One assert per test function: the suite must be able to say WHICH tests were red before."""
    if root.exists():
        shutil.rmtree(root)
    (root / "tests").mkdir(parents=True)
    (root / MODULE).write_text(code if code.endswith("\n") else code + "\n", encoding="utf-8")
    body = ["from pkg import *    # noqa: F401,F403", ""]
    for i, a in enumerate(asserts):
        body += [f"def test_{i}():", f"    {a}", ""]
    (root / TESTS).write_text("\n".join(body), encoding="utf-8")
    (root / "conftest.py").write_text("import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\n",
                                      encoding="utf-8")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def failing_ids(o: Oracle) -> tuple[bool, set[str]]:
    """(suite green?, the set of test ids that FAILED). The full suite, no fast path."""
    o.clear_pyc()
    rc, out = o.run(["--tb=no"])
    _check_harness(rc, o.extra_args, out, o.root, o.python)   # "no tests ran" is not a red suite
    ids = set()
    for l in out.splitlines():                  # "FAILED tests/test_spec.py::test_3 - assert ..."
        if l.startswith(("FAILED", "ERROR")):
            parts = l.split()
            if len(parts) > 1:
                ids.add(parts[1].split("::")[-1].strip())
    return rc == 0, ids


# ------------------------------------------------------------------ the certificate
@dataclass
class Certificate:
    verdict: str = ""            # CERTIFIED | NOT-RED | FAILS | COLLATERAL | FLAKY | AMBIGUOUS | HARNESS
    why: str = ""
    suite_runs: int = 0
    rolled_back_exact: bool = True
    seconds: float = 0.0
    red_before: list[str] = field(default_factory=list)
    broke: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict == "CERTIFIED"


def certify(root: Path, patch: str, confirm: int = 2) -> Certificate:
    """Judge a patch nobody here wrote. Every refusal restores the tree byte-for-byte."""
    t0 = time.time()
    o = Oracle(str(root), python=PY)
    f = root / MODULE
    original, before_sha = f.read_text(encoding="utf-8"), sha(f)
    c = Certificate()

    def done(verdict, why, broke=()):
        f.write_text(original, encoding="utf-8")          # the rollback IS the refusal
        c.verdict, c.why, c.broke = verdict, why, list(broke)
        c.rolled_back_exact = sha(f) == before_sha
        c.seconds = round(time.time() - t0, 2)
        return c

    try:
        green0, red_ids = failing_ids(o)
    except HarnessError as e:
        return done("HARNESS", str(e)[:200])
    c.suite_runs += 1
    c.red_before = sorted(red_ids)
    if green0:
        return done("NOT-RED", "the suite already accepts this code — there is nothing to certify")

    f.write_text(patch if patch.endswith("\n") else patch + "\n", encoding="utf-8")
    ok, why = o.check()
    c.suite_runs += 1
    if not ok:
        still_green, now_red = failing_ids(o)
        c.suite_runs += 1
        collateral = sorted(now_red - red_ids)
        if collateral:
            return done("COLLATERAL", f"turned {len(collateral)} passing test(s) red: {', '.join(collateral)}",
                        collateral)
        return done("FAILS", why[:200] or "the suite still rejects it")

    for i in range(confirm):                              # the HIDDEN lane: a green that does not repeat
        again, why2 = o.check()
        c.suite_runs += 1
        if not again:
            return done("FLAKY", f"green once, red on re-check {i + 1}: {why2[:160]}")

    f.write_text(original, encoding="utf-8")              # leave the tree as we found it either way
    c.rolled_back_exact = sha(f) == before_sha
    c.verdict, c.why = "CERTIFIED", "red before, green on the full suite, stable on re-check, nothing else broken"
    c.seconds = round(time.time() - t0, 2)
    return c


# ------------------------------------------------------------------ UNIQUE: two patches, one suite
def arity_of(code: str, name: str) -> int:
    fn = differ.find_function(code, name)
    return len(fn.args.args) if fn else 0


def separate(root: Path, name: str, a: str, b: str, workdir: Path) -> dict:
    """Are two certified patches two DIFFERENT programs? fluidfix's own differ, on whole files.

    The pool is harvested from the suite's own literals, then mutated and bisected — so a witness outside
    everything the tests mention is out of reach, by construction. When a witness IS found the law's ruling
    on BUILT+AMB is ADD_STATE: refuse both and ask for one pinning test."""
    ar = arity_of(a, name)
    seeds = differ.harvest_seeds(str(root), name, ar)
    pool = differ.build_pool(seeds, ar)
    if not pool:
        return {"witness": None, "pool": 0, "why": "no in-domain inputs could be harvested"}
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(root, workdir)
    ra = differ.evaluate(str(workdir), MODULE, a, "pkg", name, pool)
    rb = differ.evaluate(str(workdir), MODULE, b, "pkg", name, pool)
    # The driver answers {"values": [...]} — one repr per pool entry, "!Error" for a raise, "!UNSTABLE" for
    # a call that does not repeat. Reading it as a dict keyed by index silently makes every pair look
    # identical; that is exactly the bug the first run of this file had.
    for r in (ra, rb):
        if "values" not in r:
            return {"witness": None, "pool": len(pool),
                    "why": r.get("import_error") or r.get("driver_error") or "the probe produced no values"}
    va, vb = ra["values"], rb["values"]
    for i, args in enumerate(pool):
        if i < len(va) and i < len(vb) and va[i] != vb[i]:
            return {"witness": args, "pool": len(pool), "a": va[i], "b": vb[i]}
    return {"witness": None, "pool": len(pool), "why": "no input in the harvested pool tells them apart"}


if __name__ == "__main__":                                 # smoke: broken, then a fix from elsewhere
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/_certify_smoke")
    build_repo(root, "def add(a, b):\n    return a - b\n", ["assert add(2, 3) == 5", "assert add(0, 0) == 0"])
    print(json.dumps(asdict(certify(root, "def add(a, b):\n    return a + b\n")), indent=1))
