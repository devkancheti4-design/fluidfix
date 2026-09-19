# Superoptimizer task — the placement law

A taught class is producing wrong repairs. The body is asking a question it has no right to answer with an
`if`. Find the law.

---

## The defect, measured

`examples/taught-2026-09-16/rules_session.py`, class 7 `len-as-last-index`, taught from one worked example
in click's `utils.py` (`last_index = len(words)` → `len(words) - 1`). Its applier inserts ` - 1`
**immediately after** the closing paren of `len(...)`:

```python
for m in re.finditer(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])", line):
    out.append(line[:m.end()] + " - 1" + line[m.end():])
```

Measured on 12 generated instances per form, each carrying a test that catches the bug, the suite judging:

| the shape of the line | repaired | what it proposes |
|---|---|---|
| `last = len(x)` — the shape it was taught on | 12/12 | `len(x) - 1` |
| `off + len(x)` | 12/12 | correct by associativity |
| `min(99, len(x))` | 12/12 | the insertion lands inside the parens |
| **`k * len(x)`** | **0/12** | `k * len(x) - 1`, which is `(k·len) − 1`, not `k·(len−1)` |

And it shipped a **wrong repair into rich** that rich's own suite accepted
(`research/real-history-2026-09-19`):

```
line               pos = int((cut / cell_length) * len(text))
class 7 proposed   pos = int((cut / cell_length) * len(text) - 1)     ← shipped, wrong
the maintainer     pos = int((cut / cell_length) * (len(text) - 1))   ← never among the candidates
```

Over 1,452 combinations of `len(text)` and `cut / cell_length` those two disagree on **736**.

**The class generalised its signal but not its semantics.** The signal correctly finds every `len(...)`
that could be a last-index mistake. The applier only produces a correct line for the shape of its own
example.

---

## What must not be done

Do not add `if the operator is one of * / // % ** : wrap else trail`. That is the body deciding, and this
repository's rule is that **the law decides and the body only measures** — the same rule that produced the
engine, ranking, SIGHT, lanes, router and PAIR kernels.

The body's job here is to measure the syntactic context into an integer. The law's job is to turn that
integer into a placement.

---

## The measurement the body will supply

For the `len(...)` call under consideration, the body computes two precedence classes, each the
tightest-binding operator adjacent to it **within its own bracket scope** (a `(`, `[`, `{` or a comma
resets the scope):

| class | operators |
|---|---|
| 0 | nothing in this scope — after `=`, `,`, `(`, `return`, start of line |
| 1 | comparisons `< <= > >= == != in is` |
| 2 | `\|` `^` `&` |
| 3 | `<<` `>>` |
| 4 | `+` `-` |
| 5 | `*` `/` `//` `%` `@` |
| 6 | `**`, unary `-` `+` `~` |

`L` = the class on the left, `R` = the class on the right. Both in `0..6`.

**Situation word:** `x = (L << 3) | R` — six bits, 49 reachable values.

---

## The law to find

```
place(x) -> 0 = TRAIL   insert " - 1" after the closing paren of len(...)
            1 = WRAP    replace len(...) with (len(...) - 1)
```

**The property being encoded:** appending ` - 1` is equivalent to subtracting one from `len(...)` exactly
when nothing on either side binds tighter than binary minus — that is, when `max(L, R) <= 4`.

### Truth table — all 49 cases

```
L=0  x= 0..6   WRAP bits for R=0..6:  0 0 0 0 0 1 1
L=1  x= 8..14                          0 0 0 0 0 1 1
L=2  x=16..22                          0 0 0 0 0 1 1
L=3  x=24..30                          0 0 0 0 0 1 1
L=4  x=32..38                          0 0 0 0 0 1 1
L=5  x=40..46                          1 1 1 1 1 1 1
L=6  x=48..54                          1 1 1 1 1 1 1
```

As a bitmask over `x`, bit set ⇒ WRAP: `0x7F7F6060606060`

24 of the 49 reachable cases are WRAP. Values of `x` with `L>6` or `R>6` are unreachable and the law may do
anything with them.

---

## Constraints

- **Branchless integer arithmetic over `x`.** No conditionals, no table lookup, no string inspection. The
  existing laws are of this character — for example the engine's
  `act = (4 & ntzb(x-7)) + ntzb(x + (x&128))`, with SHIP iff `(x & 0x7E) == 0`.
- Shifts, masks, adds, subtracts, and `ntzb` (count trailing zero bits) are available. Prefer fewer
  operations.
- The law must be **total** on `0..63` and correct on all 49 reachable values.
- Return `0` or `1`, or a value whose low bit is the answer — state which.

---

## How it will be judged

1. **Exhaustively against the table**, all 49 reachable `x`.
2. **Against the four measured forms**, regenerated with fresh names and values, each with a test that
   catches its bug — the target's own suite accepting the repaired line is the only acceptance.
   `k * len(x)` must go from 0/12 to 12/12 and the other three must stay at 12/12.
3. **Against the rich incident**: on `pos = int((cut / cell_length) * len(text))` the law must rule WRAP,
   so the applier proposes `(len(text) - 1)` — the line the maintainer committed — instead of the line
   that shipped wrong.
4. `fluidfix selfcheck` must still re-derive every existing law unchanged.

---

## Why it is worth a law rather than a patch

This is not specific to `len`. **Every applier that inserts a token into an existing expression has the
same question** — `+ 1`, `- 1`, a negation, a clamp — and every one of them is currently answering it by
accident of where the regex matched. One placement law serves all of them, and the four classes taught so
far would each be re-checked against it.
