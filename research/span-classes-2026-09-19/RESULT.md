# Teaching it five-line edits — and a claim of mine that was wrong all session

## Insertions were never impossible

I said it repeatedly, in commits and on a published page: *"every act transforms a line that is already
there, so no line-rewriting vocabulary can express an insertion, however much it is taught."* It is false.

A candidate is spliced into the file **as a string**. A candidate containing a newline becomes several
lines. `loop._restored_original` has always compared a *span* — `new_line.split("\n")` — so the product
anticipated multi-line candidates. **The limit was in every applier anyone had written, not in the
vocabulary.**

The motive for looking: of 552 real single-file fix commits, **37% replace one line and 70% are five lines
or fewer**. Everything between those two numbers was unreachable for no reason but habit.

## Two span classes

```python
mutating-call-missing-its-return    xs.pop()  ->  xs.pop()
                                                  return xs
name-used-but-never-imported        def f(…)  ->  from math import ceil
                                                  (blank)
                                                  def f(…)
```

Both were seen twice each in the model-bug corpus, by different writers, which is the only evidence that a
shape is worth a slot.

## Fair test 1 — instances no class has been shown

Twenty-four distinct generated instances: six methods (`append`, `insert`, `add`, `extend`, `sort`, `pop`),
own names, own values, own shells, each with a test that catches it.

| | repaired |
|---|---|
| the one-line vocabulary | **0 / 24** |
| the span classes | **24 / 24** |

## Fair test 2 — the real model-written faults, untouched since collection

| | repaired | which |
|---|---|---|
| the one-line vocabulary | 1 / 14 | `insert_sorted`/phi4 |
| the span classes | **5 / 14** | `insert_sorted` ×3 writers, `percentile` ×2 writers |

The four new ones are **exactly the faults the edit-budget ladder classified as `INSERTION` — "the fix is a
line that is not there, unreachable however much is taught"**. That classification was wrong.

## Held out: suite-accepted is not correct

Every repair re-checked on inputs its own tests never used:

| fault | writer | held-out |
|---|---|---|
| insert_sorted | gemma3:4b | 4 of 4 correct |
| percentile | gemma3:4b | 4 of 4 correct |
| percentile | phi4-mini | 4 of 4 correct |
| insert_sorted | qwen3.5:4b | 4 of 4 correct |
| **insert_sorted** | **phi4-mini** | **wrong** — `([1,4,6], 5)` → `[1,5,4,6]` |

**So 4 of 14 correct, where it was 0 of 14 before.**

## The correction that matters more than the gain

That last row is not new. It is the study's **original** single repair, and it has been quoted as *"fluidfix
repaired 1 of 14 free and verified, zero wrong"*.

```
if items[i] > value:   ->   if items[i] < value:
```

passes all three of its tests and returns `[1, 5, 4, 6]` for `insert_sorted([1, 4, 6], 5)`. It inserts after
the first element *smaller* than the value. **The "zero wrong" was never established — the repair was
accepted by three assertions and never held out.** Of the 14, the honest prior figure is **0 correct**, not
1, and the "zero wrong" claim is withdrawn.

Both numbers move in opposite directions at once: the vocabulary reaches far more than I said, and the one
thing it had reached was wrong.

## Not claimed

- Two span classes, chosen because their shapes recurred across writers. Nothing here says five-line edits
  in general are reachable — only that insertions are, and that two specific recurring ones now are.
- The held-out inputs are hand-written per fault, four each. That is a check, not a proof.
- The `name-used-but-never-imported` class carries a table of eleven known names. A name outside it is
  invisible, and a wrong guess would be rejected by the suite rather than caught by the class.
- 24 of 24 is on generated instances of shapes the class was built for. The honest generalisation claim is
  the same as before: **within a taught shape, no failure found.**
