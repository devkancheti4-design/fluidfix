# Deciding the Action's default mode by measurement

The action ships `mode: push` — a repair is committed straight back to the
branch. A Marketplace listing means strangers run that on repositories nobody
has measured, so the default should be chosen on evidence.

Run it: `python3 research/action-default-2026-09-08/run.py`

## Result, 13 valid cases

| outcome | n |
|---|---|
| repaired, **byte-identical to pristine** | 10 |
| refused / left alone | 3 |
| **repaired WRONG — what `push` would have committed** | **0** |

Out-of-vocabulary defects refused (2/2). A defect no test can see was left alone.

## What this does NOT establish

Thirteen small synthetic modules is **not a base rate**. It says the obvious
failure modes are covered; it does not say "0% wrong in the wild". The honest
comparison remains the 15.4%-wrong figure measured on *deliberately weak* suites
before the 0.15.0 ambiguity fix, which has not been re-measured at that scale.

## Three corpus bugs, found before they became fake results

Every one of these would have reported MY error as the tool's behaviour:

1. **A case imported a name that did not exist** (`from mod import idx` for a
   function called `head`), so the suite failed to collect and the guard
   correctly refused a broken harness. Scored blindly, that reads as a miss.
2. **A "defect" that no assertion could see** — `cap(v,lim)` with `<` vs `<=`
   returns the same value on every asserted input. "Green" was correct.
3. **The validator itself reused stale bytecode.** A one-token edit keeps the
   file the SAME SIZE, and two writes inside one second let Python reuse the
   cached `.pyc`, so the defect never took effect and **10 of 15 good cases were
   rejected as invalid**. fluidfix's own oracle calls `clear_pyc()` for exactly
   this reason; the harness measuring it did not.

The corpus now refuses to score any case that is not GREEN on the pristine module
and RED on the defect.

Three further cases repaired where the corpus expected a refusal. All three were
wrong expectations, checked individually — e.g. `B6` asserts `abs(gap(3,3))==0`,
where `a-b` and `b-a` both pass, but `b-a` is **not reachable in one edit** from
the defect `a+b`, so only one green exists and shipping it is correct.

## Recommendation

**Keep `push` as the default for Python, and gate it on the uniqueness check.**

0.15.0 measures whether two passing candidates are actually different programs,
and records `amb_measured`. On C, C++, Java and C# that probe cannot run, so the
flag is False and the repair carries no uniqueness proof. Those are precisely the
repairs that should not be committed unattended by a stranger's CI.

Concretely: the action should push when the repair is byte-exact and its
uniqueness was measured, and fall back to reporting when it was not.
