#!/usr/bin/env python
"""Verify (not rediscover) the six constants the coordinator named, plus the
outcome each one changes.  Everything here is pure-function evidence: no
suite is run, no repo is mutated.
"""
import inspect
import os
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix import guard, loop, acts                          # noqa: E402
from fluidfix.sight import observe_bits, sight                  # noqa: E402

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"


def line(fn, n):
    return open(os.path.join(SRC, fn)).read().split("\n")[n - 1].strip()


print("=" * 72)
print("C1  coverage credibility floor -- coracle.py:715")
print("=" * 72)
print(f"  715: {line('coracle.py', 715)}")
print(f"  743: {line('coracle.py', 743)}   <- a SECOND, undocumented floor")
print("  outcome it changes: `credible` gates the candidate-set DROP at 741-744.")
print("  Simulating the two branches on a 4-file vs 5-file failing-coverage set:")
for n in (4, 5):
    fail_cov = {f"src/f{i}.c": {1, 2} for i in range(n)}
    real = [r for r in fail_cov if not guard._is_test_path(r)]
    credible = not (len(real) < 5)
    print(f"    len(real)={len(real):>2}  credible={credible!s:<5} "
          f"-> drop-non-executed = {credible}")

print()
print("=" * 72)
print("C2  default confirmation count -- loop.py:94-106 (_confirm_runs)")
print("=" * 72)
print(f"  104: {line('loop.py', 104)}")
for v in (None, "0", "1", "3", "junk"):
    if v is None:
        os.environ.pop("FLUIDFIX_CONFIRM", None)
    else:
        os.environ["FLUIDFIX_CONFIRM"] = v
    print(f"    FLUIDFIX_CONFIRM={str(v):<6} -> _confirm_runs()="
          f"{loop._confirm_runs()}")
os.environ.pop("FLUIDFIX_CONFIRM", None)
print("  outcome: 0 disables the HIDDEN lane entirely (loop.py:357 `and "
      "_confirm_runs()`),")
print("  so a one-run green is SHIPped -- the lane that dropped the measured")
print("  14% false-accept rate to 0 is switched off by an env var.")

print()
print("=" * 72)
print("C3  file_share escalation cap -- guard.py:591-592")
print("=" * 72)
for n in (589, 590, 591, 592, 596, 597):
    print(f"  {n}: {line('guard.py', n)}")
print("  outcome: caps ONE file's escalation slice. Two different formulas:")
print("    --budget given      -> (remaining wall clock) / 2")
print("    --budget not given  -> escalate_budget / 2  (a CONSTANT 300s,")
print("                           independent of how much clock is left)")
sig = inspect.signature(guard.guard_once)
print(f"  escalate_budget default = {sig.parameters['escalate_budget'].default}")
print("  Divergence, measured by substitution (no clock consumed):")
for spent in (0, 300, 550):
    remaining = 600 - spent
    a = remaining / 2
    b = 600 / 2
    print(f"    {spent:>3}s spent, {remaining:>3}s left: "
          f"budget-mode share={a:>5.1f}s   no-budget-mode share={b:>5.1f}s"
          f"{'   <- exceeds the clock left' if b > remaining else ''}")

print()
print("=" * 72)
print("C4  harvest cap -- loop.py:346 and loop.py:407 (per REPAIR CALL)")
print("=" * 72)
for n in (61, 346, 351, 407, 412):
    print(f"  {n}: {line('loop.py', n)}")
print(f"  guard.py:719: {line('guard.py', 719)}   <- a SECOND cap on the "
      "same data")
print("  outcome: HARVEST_COUNTEREXAMPLE's payload. Note the cap is per")
print("  repair() call, but guard_once CONCATENATES tried_log across files")
print("  (guard.py:518, 598), so the report cap is 200 while each file")
print("  contributes at most 64.")

print()
print("=" * 72)
print("C5  SIGHT SMALL bound -- guard.py:287  (spec: sight.py:21)")
print("=" * 72)
print(f"  287: {line('guard.py', 287)}")
print(f"  sight.py:21 spec: {line('sight.py', 21)}")
print("  Does the bound change the LAW's ruling? Sweep n_fail with every")
print("  other circumstantial bit off and specificity in the middle band:")
prev = None
for n_fail in (1, 79, 80, 81, 300):
    b = observe_bits(small=0 < n_fail < 80)
    p = sight(b)
    mark = "  <-- ruling changes here" if prev is not None and p != prev else ""
    print(f"    n_fail={n_fail:>4}  SMALL={0 < n_fail < 80!s:<5} "
          f"byte={b:>3}  sight()={p}{mark}")
    prev = p
print("  and with a POINTING bit set, the same sweep:")
for n_fail in (79, 80):
    b = observe_bits(framed=True, small=0 < n_fail < 80)
    print(f"    n_fail={n_fail:>4}  FRAMED=True byte={b:>3}  sight()={sight(b)}"
          "   (R1: pointing dominates, bound is inert)")

print()
print("=" * 72)
print("C6  test-path whitelist -- guard.py:111-115")
print("=" * 72)
for n in range(111, 116):
    print(f"  {n}: {line('guard.py', n)}")
print("  see testpath_probe.out and testpath_realrepos.out")
print()
print("BONUS: the candidate cap the coordinator did not name")
print(f"  acts.py:376: {line('acts.py', 376)}")
print(f"  candidate_cap() = {acts.candidate_cap()}  "
      f"(env FLUIDFIX_CANDIDATE_CAP)")
