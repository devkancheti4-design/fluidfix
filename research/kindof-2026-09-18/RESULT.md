# The way back: a fault's kind, measured instead of read — 2026-09-18

`../model-bugs-2026-09-18` sorted thirteen model-written faults into three kinds and admitted underneath
that the sorting was *"my reading of the code, not a measurement."* This measures it, and **the measurement
disagrees with the reading by a factor of four.**

## The method

A fault's kind is not an opinion about how the code looks. It is **the smallest class of edit the suite will
accept** — the same net, grown over edit budgets instead of territories, with the same rulings:

| level | budget | who pays | verdict if the suite accepts |
|---|---|---|---|
| L0 | fluidfix's shipped + taught classes | **$0** | MECHANICAL |
| L1 | exactly one existing line replaced by one line, no imports added | a model | ONE-LINE-TEACHABLE |
| L2 | lines may be **added**; no existing line may change | a model | INSERTION |
| L3 | anything | a model | STRUCTURAL |

REFUTED at a level grows **wider** — the next budget up. The first level the suite accepts stops the ladder.

**A model cannot cheat its level.** Every returned patch has its diff checked against the budget
mechanically before the suite ever runs, so an "L1" answer that adds a line is rejected *as an L1 answer*.
Two of the fifteen answers were rejected exactly that way (`-14 +1`, and `6h -5 +11`).

## Result: fourteen real model-written faults

| kind | n | what it means for a line-rewriting vocabulary |
|---|---|---|
| MECHANICAL | 1 | already repaired, $0 |
| **ONE-LINE-TEACHABLE** | **11** | a single line replacement exists that the suite accepts |
| INSERTION | 1 | the fix is a line that is not there — unreachable however much is taught |
| STRUCTURAL | 1 | the algorithm, not the line |

### The correction

The hand classification published this morning, against the measurement:

| | by reading | by measurement |
|---|---|---|
| reachable by a one-line edit | 4 + 1 mechanical = **5** | 1 + 11 = **12** |
| beyond any line rewrite | **9** | **2** |

**I called nine of thirteen out of reach. Two are.** And the reason I was wrong is the interesting part.

I judged the kind from the shape of the broken code and *the fix I happened to think of*. Two of the three
faults I called "insertions" — a missing `from math import ceil`, a missing `return` — have one-line
replacements that avoid the insertion entirely:

```
- rank = ceil(p / 100 * n)              - items.insert(index, value)
+ rank = int(-(-p * n // 100))          + return items.insert(index, value) or items
```

Integer-ceiling arithmetic needs no import. A mutating call can return its collection on the same line. So
**"this one needs an insertion" was a statement about my imagination, not about the fault.** Only `backoff`
— which returns scalars where the spec wants a list, across three branches — genuinely required adding a
line, and only `trim_to_fit` genuinely required the algorithm.

## Where the budget leaks, measured too

"Exactly one line replaced" is gameable, and the model answering L1 found the hole immediately: replace a
function's **docstring** with `return list(range(start, 0, -1))` and leave the whole original body
underneath as dead code. One line by the diff; nothing any vocabulary would ever propose.

So the level is checked, not merely counted — a replaced line that was a docstring or comment, or an edit
that leaves statements after an unconditional return, is flagged. **1 of the 11 games the budget**
(`countdown`), and the mechanical check flagged the same case a human reading flagged.

## The honest gap between this and a product claim

A one-line fix **existing** is not the same as a taught class **finding** it. A class needs a signal that
says which lines can exhibit it and an applier that generalises. Reading the eleven edits:

- **nine look like real recurring classes** — a missing separator before an appended token (×2), a mutating
  call where the caller wants the collection (×2), a float ceiling written without its import (×2), a
  chunking `range` where a sliding window was meant, an inline guard on a possibly-zero denominator, a
  clamp on a computed index
- **one crams the whole algorithm into a comprehension** on the `return` line — a fix, not a class
- **one games the budget**

So the defensible ceiling for a *taught* line-rewriting vocabulary on these faults is about **10 of 14**,
not the 5 of 14 published this morning, and not the 12 the raw ladder reports.

## Not claimed

- Fourteen faults, one writer per level. The L1/L2/L3 answers come from a single model; another might find
  a one-line fix where this one said impossible, which would move a fault *down* the ladder, never up.
- The ladder gives an upper bound on the fault's kind, not a proof: "no one-line fix was found" is not
  "no one-line fix exists".
- Whether the nine plausible classes actually recur across repositories is unmeasured here. The taught
  classes in `../examples/taught-2026-09-16` were measured for recurrence; these are not.
