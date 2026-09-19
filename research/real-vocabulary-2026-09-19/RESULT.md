# Teaching it the real vocabulary — what the ceiling is actually made of

"2 of 57" is a teaching-coverage figure, so the obvious move is to teach more. This looks at every real
one-line fix the vocabulary cannot express and asks what a class would have to *know* to reach it.

## One class was narrow for no reason

The shipped `literal-off-by-one` only **decrements** — it was taught from an incident where a literal was
one too large, and carried that direction as if it were part of the fault. `rich/cells.py`'s fix is
`return 0` → `return 1`. Widening the class to try both directions costs nothing and is the same defect
shape the audit already found twice: the signal generalises, the applier keeps its example's assumption.

**2 → 3 of 11 one-line real fixes expressible.**

## The other eight, and what each would need

| the fix | what a class would have to supply |
|---|---|
| `if new_line:` → `and node_type != "inline"` | a conjunct that appears nowhere on the line |
| `Column(_index=index)` → `, highlight=self.highlight` | a keyword argument and its value |
| `print(error)` → `, markup=True` | a keyword argument and its value |
| `if self.record:` → `and not self._buffer_index` | a conjunct |
| `elif default_value == "":` → `isinstance(default_value, str) and …` | a type guard |
| `self.default` → `default_value` | a different identifier, which exists **elsewhere in the function** |
| regex `[a-z#\/]` → `[a-z#\/@]` | the character `@` — **which is in the failing test's input** |
| regex `…~]*` → `…~@]*` | the same `@`, the same shape, a second time |

Grouped by where the missing information lives:

- **5 of 8 need domain knowledge.** A keyword argument, a conjunct, a type guard — nothing in the line, the
  file or the failing test implies them. No vocabulary reaches these, however many slots it has.
- **2 of 8 need a character the failing test contains.** Both are the same shape ("a character class is
  missing a character"), both in rich, both titled "@ breaks …". The value is *harvestable*, which makes
  this a counterexample-harvesting mechanism rather than a taught class — the engine law already rules
  `REFUTED → HARVEST_COUNTEREXAMPLE` and nothing acts on it.
- **1 of 8 needs an identifier from the enclosing scope**, also derivable rather than invented.

So the honest ceiling on this corpus:

| with | one-line fixes reachable |
|---|---|
| the vocabulary as taught | 2 of 11 |
| + the literal class widened | **3 of 11** |
| + values harvested from the failing test | 5 of 11 |
| + identifiers from the enclosing scope | 6 of 11 |
| domain knowledge required | 5 of 11 — a model or a person |

## And a hard limit nobody has been counting

**A user dictionary owns four slots.** There are already six taught classes competing for them, which is
how `click/andor-1` came to exhaust its node budget without ever holding the class that repairs it. Widening
the literal class above meant *overwriting a slot*. Any serious teaching programme runs out of room before
it runs out of shapes, and that is a product decision, not a research one.

## What this says about the framing

The limit is not capability — inside a taught shape nothing here has found a failure. It is that **most
real one-line fixes carry a value the line does not contain**, and a line-transform vocabulary supplies
transforms, not values. The two mechanisms that would move the number most are already named by the law and
unbuilt: harvesting the counterexample, and reading identifiers from scope.

## Not claimed

- Eleven one-line fixes from three repositories. The grouping into "needs domain knowledge" and "needs a
  harvestable value" is a reading of eight diffs, not a measurement.
- The widened literal class is verified to express `return 0` → `return 1` and to leave the other ten
  unchanged. It has not been run against a suite on this corpus, and widening a signal always risks new
  false candidates.
