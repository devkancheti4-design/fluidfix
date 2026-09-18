# It cannot write the novel fix. It can certify one — measured 2026-09-18

The vocabulary reaches a mechanical subset of faults: measured on bugs models actually wrote, **one of
fourteen** (`../model-bugs-2026-09-18`). That is the honest ceiling on fluidfix as an *author*.

But authoring is only half the tool, and it is the replaceable half. The other half is the **judge**, and the
judge does not care who wrote the patch — a model, a contractor, another tool, a stranger's pull request.
This measures the judge on patches fluidfix could never have produced.

## What a certificate claims

Issued only when all six hold, each **measured**, none inferred:

| property | how it is established |
|---|---|
| RED-BEFORE | the suite rejects the code as given — otherwise there is nothing to certify |
| GREEN-AFTER | the suite accepts the patched code (`Oracle.check`: the **full** suite, never `--lf` alone) |
| STABLE | the green repeats on N independent re-runs (the engine law's HIDDEN lane) |
| NO-COLLATERAL | every test green before is still green after |
| UNIQUE | no second supplied patch is a *different program* that also passes (`differ`, on inputs harvested from the suite's own literals) |
| ROLLBACK | on any refusal the tree is byte-identical — sha256 before and after |

All six are fluidfix's own machinery, pointed at a patch it did not write.

## The corpus

Fourteen broken implementations that models actually wrote from prose alone. For each, a correct
implementation of the same specification written by **a different model** — a whole-function rewrite, plus
five adversarial classes generated mechanically so every case faces the same shapes.

The `true` patches are not near-misses of anything in the vocabulary. For `percentile`, gemma3:4b wrote a
guarded `ceil(p / 100 * n)` with no import for `ceil`; the accepted patch was Haiku's

```python
    rank = (p * n + 99) // 100
    return sorted(values)[rank - 1]
```

— a different algorithm, in different lines, using integer arithmetic instead of a missing import. No
single-line transform connects the two. fluidfix contributed nothing but the judgment.

## Result

| patch class | supplied | verdict |
|---|---|---|
| **true** — correct, written by another model | 14 | **CERTIFIED 14** |
| **wrong** — a different model's failing implementation | 9 | refused 9 (8 fails, 1 collateral) |
| **flaky** — correct but raises on half its calls | 14 | refused 14 (10 fails, 4 collateral) |
| **collateral** — fixes the red test, breaks a green one | 6 | refused 6 |
| **overfit** — a lookup table on the exact test inputs | 14 | **CERTIFIED 14 — the hole** |
| outside-near / outside-far — correct, differing beyond the suite | 13 / 14 | certified 27 |

**307 suite runs, 109 s, and the tree was byte-identical after every single refusal.** Certifying a patch
costs 4 suite runs; refusing one costs 3.

## The hole, and the thing that closes it

A patch that special-cases the test inputs is certified when it is offered **alone**, because the suite is
the only judge. A certificate is a statement about the suite, not about the author's intent.

Offered *alongside* a second patch, it is caught every time — that is what UNIQUE is for:

| rival to the true patch | separated by `differ` |
|---|---|
| the lookup table | **14 of 14** |
| differs one step from a value the suite mentions | **13 of 13** |
| differs ~10,000 away from anything the suite mentions | **0 of 14** |

The pool is harvested from the suite's own literals, then mutated and bisected, so a disagreement far
outside everything the tests mention is unreachable **by construction** — `differ`'s own docstring says so,
and this is that warning measured. Uniqueness is a local property here, not a global one.

## What the re-check actually buys

STABLE is the cheapest property to claim, so it is the one worth measuring. A correct patch that raises on a
fraction of its calls, 20 trials at each setting; the number is **false accepts** — an intermittently
failing patch that was certified anyway (`flake.py`, `FLUIDFIX_CONFIRM`):

| flake per call | confirm=0 | confirm=1 | confirm=2 | confirm=4 |
|---|---|---|---|---|
| 2% | 19/20 | 16/20 | 15/20 | 9/20 |
| 5% | 15/20 | 11/20 | 8/20 | 4/20 |
| 10% | 7/20 | 7/20 | 3/20 | 1/20 |
| 25% | 5/20 | 1/20 | **0/20** | **0/20** |

Re-checking helps and does not save you. A 25% flake is gone by confirm=2; a 2% flake survives three quarters
of the time even then. The default of 1 is a cost compromise, not a guarantee, and this table is what it buys.

## So, honestly

**The judge is the durable half.** As authors improve, the vocabulary's share of the authoring goes to zero
— Haiku wrote 32 implementations here and broke none — while the judge's job is unchanged. Every fix still
has to be shown to be right, and that is the part nothing about a better model makes unnecessary.

**What it certifies is what your suite can see.** Sound against wrong, flaky and collateral patches, 29 of
29 refused with byte-exact rollback each time. Blind to a patch that games the tests, unless a rival patch
is offered beside it.

## Not claimed

- Fourteen cases on single-function files. A certificate on a 6,000-line file costs the full suite, and the
  uniqueness probe was measured here only on functions taking literal arguments.
- The adversarial classes are generated, not found in the wild; `wrong` alone is real (another model's
  actual failing code).
- `outside-far` is certified by design — the suite cannot see it and neither can the pool. It is listed as
  a certification, not a success.
- Nothing here changes the product. It is a harness around the shipped `Oracle`, `differ` and confirm lane.
