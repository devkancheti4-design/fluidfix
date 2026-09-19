# Properties for taught classes — 2026-09-19

A function property ("the result is sorted") needs the function's semantics, so it has to be written once
per function and only helps where somebody wrote one. A taught class is not a function — it is a rewrite —
so its property is **algebraic**: a statement about the transform, true whatever code surrounds the line.

That difference is the whole value. A class property is written **once, when the class is taught**, and
then holds every future application of that class to account — in repositories nobody has cloned yet, at
**zero suite runs and zero tokens**.

| class | the property, in the English a maintainer reviews |
|---|---|
| 7 `len-as-last-index` | the candidate equals the original with `len(x)` replaced by `(len(x) - 1)`, for every length |
| 4 `flipped-boolean-operator` | flipping the token means the same as swapping that operator at its node, for every truth assignment |
| 6 `inverted-bare-guard` | the candidate is the exact negation — no value on which the two agree |
| 5 `get-without-default` | supplying a default changes only the key-absent case |

Three verdicts, and the middle one is the honest part: **PROVEN** (checked over the whole bounded domain),
**REFUTED** (a witness exists — refuse now, before spending a suite run), **UNPROVEN** (did not apply, or
nothing could be evaluated). A check that evaluates zero inputs is UNPROVEN, never PROVEN.

## Controls first

A property nothing can fail proves nothing, so every property ships with a rewrite it must refuse.

| class | control | verdict |
|---|---|---|
| 7 | `len(words) + 1` — adds instead of subtracting | REFUTED |
| 7 | `k * len(words) - 1` — the rich incident verbatim | REFUTED |
| 4 | `a and b` → `a or c` — flips an operand too | REFUTED |
| 6 | `if value:` → `if value is None:` — both false at `0` | REFUTED |
| 5 | reads a different key | REFUTED |

**5/5.** The properties have teeth.

## The gate, on 30 candidates the four classes actually propose

No repository checked out, no suite run.

| | PROVEN | REFUTED | UNPROVEN |
|---|---|---|---|
| the vocabulary as taught, 2026-09-16 | 20 | **6** | 4 |
| the same vocabulary, class 7 ruled by the placement law | **26** | 0 | 4 |

All six refusals are class 7, and one of them is `pos = int((cut / cell) * len(text) - 1)` — **the line that
shipped wrong into rich and that rich's own suite accepted**. The property catches it from algebra alone.
The four UNPROVEN are class 4 on flattened chains, below.

## What this found that nothing else had

### 1. A hole in the placement law's specification — left-hand minus

The law was verified exhaustively against its 49-case table this morning and the table was wrong. Its stated
property — "appending ` - 1` is equivalent when `max(L, R) <= 4`" — puts `+` and `-` in the same class 4.
But a minus to the **left** negates the call, so it enters with coefficient −1:

```
k - len(x) - 1      is  k - L - 1
k - (len(x) - 1)    is  k - L + 1        ← off by two, for every input
-len(x) - 1         is  -L - 1
-(len(x) - 1)       is  -L + 1
```

The fix belongs to the **body, not the law** — which is this repository's whole discipline. `_left_class`
was measuring `-` as class 4; it now measures it as 5, which forces WRAP. The law is byte-for-byte
unchanged and still scores 0 violations on all 49 reachable situation words; `fluidfix selfcheck` still
re-derives all six laws; the repo's 225 tests still pass.

Four positions nothing had tried before now hold: `k - len(x)`, `-len(x)`, `(k - len(x)) * 2`,
`abs(k - len(x))`.

### 2. Class 4 is sound where I predicted it was broken

I expected `and`/`or` flips to regroup, because `and` binds tighter. They do not: both operators are
associative and the regrouping is absorbed. Class 4 is **PROVEN over every truth assignment** on every
mixed expression tried, up to four variables and 1,296 assignments.

Where it is genuinely under-determined is a **flattened chain**. Python parses `a or b or c` as one
`Or` of three values, not two nested nodes, so "flip the first `or`" has no node-level meaning — swapping
the node's op changes all of them. The property returns UNPROVEN and the honest ruling is AMB, not a
silent ship.

### 3. Two bugs in the checking itself, both of which had produced clean-looking wrong answers

- **Operator located by node, not token.** In `a and b or c` the `Or` node and the `And` node both begin
  at column 0, so ordering by node column tied and matched the first textual `and` against the `or` node.
  7 of 13 class-4 "violations" were this bug. Fixed by locating the operator token in the gap between
  values.
- **A vacuous pass reported as a pass.** `n = j - len(a) + len(b) - 1` printed `HOLDS over 0 inputs`,
  because only the first `len()` was replaced by a free variable and the second raised on every point. Now
  every `len()` on the line gets its own free variable — the same line checks 125 real inputs — and zero
  evaluated inputs is UNPROVEN everywhere.

## Where this lives

- `src/fluidfix/props.py` — `teach_property`, `check`, `gate`; fails safe (a broken checker returns
  UNPROVEN, never passes a candidate)
- `src/fluidfix/propcheck.py` — the reusable part: `agree_over`, `free_names`, `rhs`, `nth_boolop_swapped`
- `examples/taught-2026-09-19/props.py` — the four taught properties, versioned beside the dictionary
- `load_dictionary` now supplies `teach_property` and `propcheck`, so a dictionary teaches a class's
  property the same way it teaches the class

## The honest boundary

Bounded, and the bound is in the certificate rather than implied. Class 7 ranges over lengths {1,2,3,5,8}
and class 4 over six representative values per name — a disagreement that first appears at length 21 would
be missed. What the bound buys is that the check is **algebraic**, so a single violating point is a proof
of wrongness for the rewrite everywhere, which is how one 5-value grid caught the rich incident.
