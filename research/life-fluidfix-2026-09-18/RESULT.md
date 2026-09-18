# fluidfix's taught shapes inside the Life Debugger — measured 2026-09-18

The Life Debugger (github.com/devkancheti4-design/life-debugger, AGPL-3.0) escalates cheapest-first:

    TIER 1  FACTS      static anti-patterns + the runtime error class — $0
    TIER 2  LIFE       replays a fix it has been given before — $0
    TIER 3  REASONER   a model writes a fix

Its tier 1 **names** a bug and cannot repair one, and a tier-3 fix is **trusted on sight**. fluidfix already
owns the two things that close both gaps: a vocabulary of fault **shapes**, each with a signal saying which
lines can exhibit it and an applier proposing the correction, and the rule that **only the test may accept a
candidate**. `life_fluidfix.py` inserts them:

    TIER 1.5  SHAPES   fluidfix's shipped + taught classes propose; the caller's own test judges;
                       a candidate that does not turn the test green is rolled back, $0

and puts the same judge in front of tier 3, so a model's fix is run before it is believed.

## Measured

Fifteen small programs, each with one fault and a test that catches it. Nothing is accepted on resemblance:
a fix is recorded only because that case's own test went green.

| | cases | fixed free, verified | abstained | wrong fixes | tokens |
|---|---|---|---|---|---|
| in vocabulary (shipped + taught) | 12 | **12** | 0 | 0 | 0 |
| outside the vocabulary | 3 | 0 | **3** | 0 | 0 |

Cost: the whole pass is **1.4 s** for fifteen cases, a median of **1 test run** per repair (max 5). The second
pass over the same fifteen, with the Life carrying what the first learned, is **1.0 s** and **1 run** per case
— the memory replays the shape but the test still re-verifies it, so memory never overrides the judge.
Memory after both passes: **13 rows, 835 bytes**, reproducible sha.

| shape | before → after | test runs |
|---|---|---|
| strictness | `if age > limit:` → `>=` | 1 |
| literal-off-by-one | `xs[2:]` → `xs[1:]` | 1 |
| flipped-additive | `a * b - c` → `+ c` | 2 |
| minmax-swap | `min(v, floor)` → `max` | 1 |
| flipped-augmented-assign | `t -= x` → `+=` | 2 |
| flipped-comparison-direction | `lo > hi` → `<` | 2 |
| flipped-boolean | `return False` → `True` | 1 |
| flipped-boolean-operator (taught) | `help_text and "_"` → `or` | 1 |
| get-without-default (taught) | `cfg.get("port")` → `.get("port", 0)` | 5 |
| inverted-bare-guard (taught) | `if value:` → `if not value:` | 1 |
| len-as-last-index (taught) | `len(words)` → `len(words) - 1` | 1 |
| range-start-dropped (taught) | `range(len(xs))` → `range(1, len(xs))` | 3 |

The three out-of-vocabulary cases — `lstrip` where `strip` was meant, a missing `return`, the wrong dict key —
are reported as abstentions. That is the Life Debugger's own rule ("it says *I'm not sure, ask the model*
instead of inventing a fix") and fluidfix's refusal, and they are the same rule.

## What this changes for each side

- **For the Life Debugger**: its free tier can now *repair*, not only name, for every shape in the vocabulary,
  and a model's answer is no longer taken on trust — it faces the same test.
- **For fluidfix**: the shapes work on a snippet and a one-line test, with no repository, no git and no suite
  harness. The ladder and the persistent memory come for free from the Life.

## Honest limits

- Fifteen small programs, one fault each, one-line tests. This measures the vocabulary's reach on snippets,
  not on a repository; for repositories see `research/llm-fusion-2026-09-16`.
- A user dictionary owns kinds 4–7 — **four taught classes per file** — so the five classes taught on
  2026-09-16 need two files, and each case here loads the one that carries its class. That limit is the
  product's, not the harness's.
- One malformed test was found during the run (a trailing `or True` made the and/or case unfailable) and
  fixed; the bench asserts that every case's test fails before the repair, which is what caught it.
- The reasoner tier is wired and verified-before-believed, but no model was called here: every number above
  is zero tokens by construction.
