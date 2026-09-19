# A seventh gate, built and tested — it does not work

## The idea

The six gates ask whether the suite went green. None asks **what else changed**. Both false accepts found on
real history slipped through exactly there:

```
segment.py    `- 1` outside the multiplication instead of inside it
traceback.py  a padding tuple altered 135 lines from the actual fault
```

Neither breaks a test, because no test pins those behaviours. So: *a repair may change behaviour only where
the failing test demands it.* Wrap the enclosing function, run the tests that were **already passing**, and
measure the fraction of recorded calls whose result changed. A correct repair should be near zero there; a
compensating edit should be large.

No new tests are needed, which is what made it attractive.

## The measurement — with a control

Three variants per case: the original buggy program, what fluidfix shipped, and **what the maintainer
committed**. The last is a control that would not exist at repair time; it is the whole point of running it.

| case | calls | candidate (fluidfix, wrong) | reference (maintainer, correct) |
|---|---|---|---|
| `Segment.split_cells` | 35 | 0/35 — **0%** | 0/35 — **0%** |
| `Traceback.__rich_console__` | 16 | 16/16 — **100%** | 16/16 — **100%** |

**The gate has no discriminating power on either case.**

On `traceback.py` it looked like a triumph — every call under an already-passing test changed, a screaming
signal — right up until the maintainer's own fix scored exactly the same. On `segment.py` both score zero:
the passing tests only use inputs where the two formulas happen to agree.

Had I run only the candidate, I would have reported a working gate and been wrong.

## Why it fails, and it is not a matter of tuning

- **`__rich_console__` returns a rendered object.** Any change anywhere inside it changes the repr, so both
  a correct and an incorrect edit score 100%. The observation is too coarse, and making it finer means
  knowing which part of the render matters — which is the original problem again.
- **`split_cells` under the passing tests never reaches an input where the two formulas differ.** They
  disagree on 736 of 1,452 input combinations, and the suite exercises none of them. A gate that looks only
  where the suite already looks cannot see that.

The second is the general case and it is fatal to the idea as posed: **the information needed — which of two
formulas was intended — is not in the repository.** It is not in the tests, not in the behaviour under the
tests, and not recoverable by any amount of cleverness about deltas. It is in the maintainer's head, and the
only artefact that carries it is a test nobody wrote.

## What this settles

The claim that prompted it — *"the laws are flawless, the oracle is the problem"* — comes out stronger, not
weaker. The law's ruling was correct given its inputs in both cases. The oracle was wrong in both cases. And
this file is evidence that **the oracle cannot be repaired from inside the repository**: the most promising
suite-free strengthening available, built and measured against a control, distinguishes a correct repair
from a wrong one exactly zero times out of two.

What remains open is the other direction — strengthening the oracle from *outside* the repository: property
tests, a reference implementation, a second independent implementation to differ against. All of those cost
someone writing something, which is precisely what "no new tests" was trying to avoid.

## Not claimed

- Two cases. A gate that fails on two is not proven useless in general, only unproven and unhelpful here.
- The observation is the `repr` of a function's return value. A finer instrument — comparing structure
  rather than text, or watching the specific expression rather than the enclosing function — might separate
  them. That is a real avenue and it is not what was tested.
- The `segment.py` zero is partly a property of that suite: 24 tests were already failing under a modern
  interpreter and were deselected, so the surviving coverage is thinner than the project's own.
