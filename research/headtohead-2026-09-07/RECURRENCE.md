# How often is a real bug fix the shape fluidfix repairs?

Scanned every commit in three game-relevant C/C++ repositories (full clones —
a blob-filtered clone cannot produce diffs and reads near zero, which is worth
knowing if you rerun this). A commit counts if its change is a SINGLE LINE
whose diff is a SINGLE TOKEN of a class fluidfix ships: boundary, comparison,
operator, logic, sign, off-by-one. Test directories and version bumps excluded.

Reproduce: `python3 recurrence.py <path-to-a-full-clone>`

| repo | span | source commits | fix-worded | single-token | of fixes | per year |
|---|---|---|---|---|---|---|
| raylib | 12.8 yr | 6,553 | 1,236 | 137 (32 fix-worded) | **2.6%** | **10.7** |
| Box2D | 17.1 yr | 599 | 319 | 25 (14 fix-worded) | **4.4%** | 1.5 |
| cglm | 9.9 yr | 1,204 | 253 | 6 (6 fix-worded) | **2.4%** | 0.6 |

## What this actually says

**Roughly 2-4% of bug-fix commits are single-token shapes.** That is the
addressable share, and it is consistent across three independent codebases
spanning ten to seventeen years. It is not a large fraction and we will not
present it as one.

**Absolute frequency tracks commit velocity, not codebase quality.** raylib is
an actively developed game framework and produces **10.7 a year**. Box2D and
cglm are slow-moving libraries and produce 1.5 and 0.6. Same defect class, same
percentage of fixes, an order of magnitude apart in absolute count — because
one ships far more code.

## What it means for the price

At $50-150 of engineer time per defect:

    raylib-shaped project (10.7/yr)   $535 - $1,600 a year
    Box2D-shaped library (1.5/yr)     $75  -  $225 a year

**Neither justifies a $12,000 licence**, and that is the honest finding. A
licence pays for itself somewhere around 100-200 qualifying defects a year,
which is roughly 10-20x raylib's rate. That rate is plausible for a
live-service title with a large team patching weekly — and **plausible is not
measured**, which is exactly why the pilot exists and why it is the tier we
recommend first.

Against the same rates, an unaided LLM agent costs 43,006 tokens per defect
(measured, see RESULT.md), so raylib's 10.7 a year is about 460,000 tokens —
well under $10. **Token cost is not the argument for this tool.** Determinism,
refusing instead of guessing, and zero marginal cost for unattended running
are.

## Caveats
- Three repositories, all C/C++ graphics or physics. Not a census.
- "fix-worded" is a commit-message heuristic; the true fix count is higher.
- A repo's own suite must be able to SEE the defect. On cglm, 3 of 6 real
  historical one-token fixes were invisible to its own tests.
