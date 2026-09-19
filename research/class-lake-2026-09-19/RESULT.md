# The classes are a territory too — the loop, one level up

I had been auditing taught classes by hand, one at a time. That is the loop's job. A class is code with a
spec: a signal saying which lines could carry the fault, an applier saying what to put there. That makes
it a **territory**, and everything the net does to a repository it can do here.

## The territory and its judge

`classes/appliers.py` holds three taught classes. `classes/test_appliers.py` is the suite, and it is the
hand audit made executable — every case applies a class to a broken line, runs the result, and then checks
it **on a second input the case never used**. That second check is the whole point: a class proposing a
line the suite rejects is merely narrow, while one proposing a line the suite *accepts* that is wrong is a
latent false accept, and only the second input separates them.

Every case is an incident: the worked example the class was taught from, or a shape it was later found to
get wrong.

```
the classes territory is RED — 2 failing:
    test_mutating_pop_whose_call_answers_the_item
    test_len_as_an_operand_of_times
```

## The net goes in, and refuses — correctly

```
executed=8   observations=0   RESULT=NO-OBSERVATIONS   rolled back byte-exact: True
```

**With every taught class available to it, the vocabulary could not form a single candidate.** No signal
matches any line of an applier, because the faults live in *string templates* and in *where a substring is
inserted* — not in any line shape the vocabulary recognises. That is the right ruling: repairing a class's
semantics is not a mechanical line fault.

## The handoff, and the certificate

A model was given the file, the two failing tests, the specs, and the refusal. Its patch was then judged by
the classes' **own spec-derived suite**: **6 passed, stable over three re-runs.**

It found both defects, and a third I had missed:

| | |
|---|---|
| `return CALL or RECEIVER` | → `return (CALL, RECEIVER)[1]` — the answer is discarded positionally, so a truthy `pop()` can never stand in for the collection |
| ` - 1` trailed after the call | → the call is bracketed |
| the signal's lookahead `(?!\s*[-+*/%])` | **over-broad** — it suppressed repair whenever *any* operator followed, so `len(xs) * 2` and `len(xs) + 3` were refused outright. Narrowed to `(?!\s*-\s*1\b)`, which skips only an already-correct line |

Verified across eight shapes: correct everywhere, strictly wider than before, and still idempotent on
`len(xs) - 1`.

## And it makes the placement law look unnecessary

The model's applier **always brackets**. That sidesteps the placement question rather than answering it —
and always bracketing is unconditionally correct for appending a suffix to a call.

| line | the law | always-wrap | the maintainer wrote |
|---|---|---|---|
| rich's real incident | `* (len(text) - 1)` | `* (len(text) - 1)` | `* (len(text) - 1)` |
| click's teaching example | `len(words) - 1` | `(len(words) - 1)` | `len(words) - 1` |

**Both are byte-exact on the case that mattered.** The law's remaining advantage is the second row: it
produces the line a human would write, where always-wrap leaves redundant parentheses.

So the honest position on the placement law, one day after generating it: **it buys style, not
correctness**, for this class. Where it would still earn its keep is anywhere bracketing is not available —
an inserted token that is not a suffix on a parenthesised call, or a context where extra parens are
invalid. Neither is measured.

## What the level actually bought

The hand audit found two defects. The loop found the same two **plus** the over-broad signal, and it did so
from the failing tests and the specs rather than from someone remembering to look. That is the argument for
putting classes in a territory: **the audit stops depending on me running it.**

## Not claimed

- Three classes, six tests, one descent. The suite encodes the incidents already known; it does not
  generate new shapes on its own, so a defect nobody has hit yet is still invisible.
- The model's fix was certified by a suite I wrote from the same understanding that produced the defects.
  A shared blind spot would pass unnoticed in both.
- The vocabulary's refusal here is a `NO-OBSERVATIONS`, not a `REFUTED`: it never built a candidate to be
  rejected. That is a weaker statement than "it tried and failed".
