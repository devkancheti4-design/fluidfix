# Does one taught example repair novel members of its class? — measured 2026-09-16

**Question.** Teaching claims that one structured example buys a whole fault
class: every future member, in any file, with any names. Is that true for
members the example never saw, and where does it stop?

**Setup.** A four-module repo with a suite that pins values (`run.py`
builds it). Four classes taught from one worked example each (`rules.py`,
written exactly as `docs/TEACHING.md` prescribes): a lost `round()`
precision, a lost `.get()` default, a lost `.split()` separator, and a
two-line shape (rounding moved ahead of an accumulation, repaired as one
`SpanEdit`). Then ten members injected one at a time, each committed as a
shipped regression, each run through `fluidfix guard . --commit
--dictionary rules.py` exactly as maintenance would, and each judged
against the **pristine bytes** — not "the suite went green". master
`6fab7e2`, `src/` on the path. One decoy line, `return round(x)`, is correct
code that matches the taught pattern; its test pins `whole(2.7) == 3`.

Reproduce: `PYTHONPATH=../../src python3 run.py` — results in `results.json`.

| case | member | file | verdict | suite runs | reported |
|---|---|---|---|---|---|
| T1 | the taught example itself: return round(x, 2) -> round(x) | `money.py` | REPAIRED byte-exact | 7 | 2.5 |
| N1 | novel: assignment form, other name, other file position | `money.py` | REPAIRED byte-exact | 10 | 3.2 |
| N2 | novel, OUTSIDE the example's pattern: expression argument | `money.py` | REFUSED as expected | — | — |
| N2w | same member, example rewritten with a wider pattern | `money.py` | REPAIRED byte-exact | 11 | 3.4 |
| N3 | novel .get() default lost: other key, inside addition | `ledger.py` | REPAIRED byte-exact | 8 | 2.7 |
| N4 | novel .get() default lost: inside a subtraction, other file position | `ledger.py` | REPAIRED byte-exact | 8 | 2.7 |
| N5 | novel split() lost separator: return form | `parse.py` | REPAIRED byte-exact | 2 | 1.3 |
| N6 | novel split() lost separator: assignment, other name | `parse.py` | REPAIRED byte-exact | 2 | 1.4 |
| N7 | two lines wrong together (SpanEdit): the taught shape, novel names | `totals.py` | REPAIRED byte-exact | 4 | 1.7 |
| N8 | two lines wrong together: novel names, deeper indentation, inside an if | `totals.py` | REPAIRED byte-exact | 6 | 2.2 |

- **Novel members: 9 of 9 repaired byte-exact** — different files, names,
  positions, an assignment instead of a return, a subtraction instead of an
  addition, a two-line shape at deeper indentation inside an `if`. The
  example's *names* never mattered; its *shape* did.
- **Zero wrong repairs.** Every other file byte-identical after every run;
  the decoy `round(x)` was never changed — its candidate `round(x, 2)` was
  generated on every money.py case and rejected by the suite each time
  (the extra suite runs on T1/N1/N2w are exactly that).
- **The edge is the example's pattern, and it is visible.** N2 —
  `round(price * qty)`, an expression rather than a name — sat outside the
  example's `round\(\w+\)` signal and was **refused** with the tree
  untouched: REFUTED → HARVEST_COUNTEREXAMPLE, every candidate listed with
  the test that killed it. Widening the example's pattern to any non-nested
  argument (`rules_wide.py`) repaired it byte-exact in 11 runs. Nothing
  else changed. The class generalises as far as the example is written to,
  and no further; when it stops, it says so rather than guesses.

**What this establishes.** A taught class is a shape, not a lookup of the
lines it has seen: nine members the example never saw were restored
byte-exact from one example each, at zero tokens, in 3–5 s. **What it
does not.** These are purpose-built members with a suite that pins each
one; on a real history the suite's blindness, not the class, is the usual
limit (`44-author-successor-teaching`: 3 of 6 real cglm fixes invisible to
its own tests).
