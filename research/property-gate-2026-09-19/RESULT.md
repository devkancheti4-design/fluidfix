# The seventh gate: exhaustive over a bounded domain — 2026-09-19

## The claim under test

> "it can prove the fix is right with all possible inputs"

Not with a test suite, it cannot. Today produced the sharpest available proof of that. The one repair the
real-history study called "verified, zero wrong" was:

```
was  if items[i] > value:
now  if items[i] < value:
```

It passes **all three** of its bug's tests and all six certification gates. It returns `[1, 5, 4, 6]` for
`insert_sorted([1, 4, 6], 5)`. A suite is a finite set of examples; passing it is evidence, never proof.

## What is reachable

Enumerating inputs by itself does not help, because enumeration needs an oracle and the premise is that no
correct version exists to compare against. What needs no reference is a **property** — a statement true of
every input regardless of implementation:

```
insert_sorted   the result is sorted, and is a permutation of the input plus the value
```

Checked exhaustively over a bounded domain, that is a proof on that domain: not "the tests pass" but
**"no input of this size can distinguish this from correct."**

## Measured

Domain: every sorted list of length 0..4 over values 0..3, crossed with every value 0..3 — 280 inputs.
The same three model-written bugs, the same taught class, the same repairs the suite accepted.

| repair | the suite | exhaustive, 280 inputs |
|---|---|---|
| gemma3:4b-hard | accepted | **PASS** |
| phi4-mini-hard — `> value` → `< value` | accepted | **FAIL** — `[1], 0 -> [1, 0]` is not sorted |
| qwen3.5:4b-hard — same flip | accepted | **FAIL** — `[1], 0 -> [1, 0]` is not sorted |

Controls, so the property is not one that anything satisfies:

| control | verdict |
|---|---|
| a real `bisect.bisect_left` implementation | PASS over 280 |
| `def f(items, v): return []` | FAIL — `[], 0 -> []` is not the input plus the value |

The gate rejected both wrong repairs and kept the right one. It cost 280 function calls — no suite runs, no
tokens, milliseconds.

## What this costs and what it is worth

The property is a **teachable artefact, exactly like a fault class** — someone has to write it. It is worth
more per unit of effort than a class is:

- a class repairs **one shape** of fault
- a property gates **every future repair to that function, forever**, including repairs the net did not
  write and repairs a model wrote

And it is the natural companion to the taught-class design. The vocabulary is narrow on purpose; the
functions it is pointed at are the ones the engineer already knows well enough to teach. Writing down what
`insert_sorted` must always do is a thing that engineer can do in one line.

## The honest boundary

- "all possible inputs" is not achievable. **All inputs up to a bound** is, and the bound is stated in the
  certificate rather than implied.
- A property that is wrong or too weak gates nothing. `return []` failing here is the check that the
  property has teeth; every taught property needs one.
- The domain must be enumerable. `insert_sorted` over small ints is; a function taking a file handle is not,
  and for those this gate abstains rather than lying.

## Where it belongs

As gate seven, beside RED-BEFORE, GREEN-AFTER, STABLE, NO-COLLATERAL, UNIQUE, ROLLBACK — and it is the only
one of the seven whose verdict is not an opinion of the suite.
