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

## I claimed the law was cosmetic. It is not — checked again

The model's applier **always brackets**, which sidesteps the placement question, and on the two lines I
compared it was byte-identical to the law where it mattered. I concluded the law bought style rather than
correctness. **That was wrong, and the check that shows it is the project's own acceptance criterion.**

A repair counts in the real-repo study only when the line it produces equals the pre-mutation original
**byte for byte** — that is what "7 of 22 exact, zero tokens" means. Every `lenm1` original in that corpus
is unparenthesised:

```
arrow    elif index == len(timeframes) - 1:  # Must have at least 2 items
click    last_index = len(words) - 1
sorted   max_pos = len(_maxes) - 1
rich     last_column = column_index == len(self.columns) - 1
```

| | the law | always-wrap |
|---|---|---|
| byte-exact restorations | **4 / 4** | **0 / 4** |

Always-wrap produces `(len(words) - 1)` where the original had none, and fails every case. **Here style
*is* the criterion**, so the law is not decoration — it is the thing being scored.

### And my suite certified the regression

The classes' suite checked semantic correctness on a second input and never checked byte-exactness, so it
passed a patch that would have taken four previously-exact repairs to zero. The audit I was proud of had
the same shape of hole as the classes it was auditing: **it encoded what I had thought to look for.**

Both are now in the applier and both in the suite — the model's narrowed signal, which genuinely widened
the class, and the law's placement, which the criterion requires:

```
return len(xs) * 2     ->  return (len(xs) - 1) * 2      widened, was refused outright
return k * len(xs)     ->  return k * (len(xs) - 1)      the rich incident
return len(xs) + 3     ->  return len(xs) - 1 + 3        no redundant parens
last_index = len(words) -> last_index = len(words) - 1   byte-exact
```

7 passed.

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
