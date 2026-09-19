# The placement law — verified, wired in, and it generalises past its own test set

A defect was found on real history: the taught class `len-as-last-index` appends ` - 1` after the closing
paren of `len(...)`, which is right where `len(...)` is the whole right-hand side — the shape of its one
worked example — and wrong under any operator binding tighter than `-`. It shipped `* len(text) - 1` into
rich where the maintainer had written `* (len(text) - 1)`, and rich's own suite accepted it.

The body was deciding where a token goes. A law now decides.

## The law, as delivered

```c
static inline int32_t L_LEFT (int32_t x) { return ((x + 24) >> 6); }
static inline int32_t L_RIGHT(int32_t x) { return (((x + 3) >> 3) - (x >> 3)); }
int32_t place(int32_t x) { return L_LEFT(x) | L_RIGHT(x); }   /* 0 TRAIL, 1 WRAP */
```

with `x = (L << 3) | R`, the precedence class of the operator adjacent to the call on each side.

**The algebra checks out independently of its own harness.** `x = 8L + R`, so `x + 24 = 8(L+3) + R`, which
reaches bit 6 exactly when `8L + R ≥ 40` — and since `R ≤ 6`, that is exactly `L ≥ 5`: the carry *out* of
the left field. And `(x+3)>>3 = L + [R ≥ 5]`, so subtracting `x>>3 = L` leaves precisely the carry *into*
the left field. Two thresholds, seven operations, no branch, no table.

Compiled and run: **0 violations** — exhaustive over all 49 reachable words, the stated bitmask
`0x7F7F6060606060` reproduced, 24 WRAP cases as specified, total on 0..63, each lane equal to its own
field's threshold.

## What the delivered file asserted rather than measured

Criteria 2 and 3 hardcode `L` and `R` for the four forms. That tests the law and not the body, so the body
was written (`src/fluidfix/place.py`) and the situation measured off real lines — adjacent operator per
side, skipping balanced brackets, with `(`, `[`, `{` and `,` resetting the scope. On twelve hand-read
lines the measurement disagreed **zero** times, including `a * b + len(x)` → TRAIL (the `*` binds `a*b`,
not the call) and `a + b * len(x)` → WRAP.

## The acceptance that matters: the suite judging, not the table

Twelve generated instances per form, each carrying a test that catches its bug, `shapes_repair` proposing
and the test accepting:

| form | before | after |
|---|---|---|
| `len` is the whole right-hand side — the taught shape | 12/12 | 12/12 |
| `len` as an operand of `+` | 12/12 | 12/12 |
| **`len` as an operand of `*`** | **0/12** | **12/12** |
| `len` inside a call | 12/12 | 12/12 |
| **`t // len(x)` — a form in no example and no prior case** | **0/12** | **12/12** |

The last row is the one worth having. It was never taught, never measured before, and appears in none of
the four forms the law was posed against. **The law reached it because it rules the situation rather than
the shape**, which is what the earlier generalisation claim asserted without evidence.

## The rich incident

```
the law proposes   pos = int((cut / cell_length) * (len(text) - 1))
the maintainer     pos = int((cut / cell_length) * (len(text) - 1))
what shipped wrong pos = int((cut / cell_length) *  len(text) - 1)
```

**Byte-exact with the line the maintainer committed** — and that line was never among the candidates before.

`SELFCHECK PASS — 6 laws re-derived`, unchanged.

## Not claimed

- **Minimality is the search's claim, not mine.** `L_LEFT` is stated MINIMAL in D ∩ I ∩ I2 and proved by
  the tool that produced it; nothing here verifies that, only correctness.
- The measurement is a scanner over source text, and it is the part that will break first. Twelve lines
  agreed with a hand reading; a line with a lambda, a walrus, a conditional expression, or an operator
  split across a continuation has not been tried.
- The old class is left in place. `examples/taught-2026-09-16/rules_session.py` is checksummed and quoted
  in the sales material; the law-driven version is a **new** dictionary,
  `examples/taught-2026-09-19/rules_placed.py`.
- This fixes one wrong repair of the two found on real history. The other — a padding tuple changed 135
  lines from the fault — is not a placement error and is untouched by this.
- The 57-case result stands: 0 correct repairs. This removes a cause of one wrong ship; it does not add a
  right one.
