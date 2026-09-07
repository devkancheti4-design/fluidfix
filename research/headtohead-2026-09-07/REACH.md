# How much of real bug-fixing is within reach — the 50% question

Not "how many fixes match a catalogue" (RECURRENCE.md) and not "how many are one
token" (CEILING.md), but the architectural question: **how many real bug fixes
are small and local enough for a taught class to express?** `SpanEdit` already
does multi-line, so the bound is one file, a few lines, in a learnable shape.

Reproduce: `python3 reach.py <path-to-a-full-clone>`

| repo | fix commits | touch ONE file | one file, one hunk | crosses 50% at |
|---|---|---|---|---|
| raylib | 1,041 | **85.4%** | 35.2% | **≤ 9 changed lines** |
| cglm | 225 | **60.9%** | 30.2% | **≤ 14 changed lines** |
| Box2D | 300 | 41.3% | 23.0% | **never — tops out at 41.3%** |

## The answer

**"More than half of bugs" is measurably true on two of these three
repositories** — if a taught class can span roughly ten lines inside one file.
raylib crosses 50% at nine changed lines; cglm at fourteen. That is far above
the 2-4% the shipped six classes cover, and above the 7-16% single-line ceiling.

**Box2D never crosses it, and the reason is not shape or size.** 59% of its fix
commits touch MORE THAN ONE FILE. No line budget reaches them, because the limit
is not how much a class can express — it is that the search is single-file by
construction.

## So the binding constraint is multi-file, not entropy

The distribution says the same thing three times:

  * one file, any size            41-85% of fixes
  * one file, one contiguous hunk 23-35%
  * one file, <= 3 lines          16-23%

Line count is cheap to widen; a taught span already covers it. **Crossing from
~35% to ~85% on raylib means repairing more than one site.**

That lane already exists and is already verified. The PAIR law's `PARTITION`
ruling is precisely this case: when the failing tests split into independent
groups, the situation is N separate single-bug repairs — linear, not
combinatorial. It is fused, exhaustively checked over all 256 situations, and
**not actuated**. A separate measurement showed a genuine two-bug fixture where
PARTITION turns a refusal into a green suite in one extra 2.7-second pass.

**That is the honest roadmap to the 50% claim:** not a bigger vocabulary, not
cleverer classes — actuate PARTITION and let the search repair disjoint sites
one at a time.

## Caveats
- Three C/C++ repositories. "fix-worded" is a commit-message heuristic.
- Being *reachable* is not being *repaired*: the repo's own suite must still see
  the defect, and on cglm 3 of 6 real one-token fixes were invisible to its own
  tests. Reach is a ceiling, not a hit rate.
