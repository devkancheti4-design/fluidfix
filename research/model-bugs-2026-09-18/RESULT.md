# Can it repair the bugs a model writes? — measured 2026-09-18

The claim worth testing, since it is the one a buyer will make first: *AI writes buggy code, so a free
mechanical repairer should pay for itself.* Half of that is true, and the half that is not matters more.

## Method

Sixteen small functions, specified in prose only — a signature and a docstring. The writer never sees the
tests. Two sets: `specs.py` (ordinary utilities) and `specs_hard.py` (the same size, but each turning on a
boundary: a ceiling, an exclusive bound, a half-open interval, a nearest rank). Nothing in either set was
chosen because fluidfix can repair it.

Four writers: three local models through Ollama (qwen3.5:4b, phi4-mini, gemma3:4b) and Claude Haiku as a
sandboxed subagent that read the specs and nothing else. Every implementation is then run against the
hidden tests. The failures are real, unseeded, model-authored bugs.

Each failure is handed to fluidfix with those same tests as the only judge, using the five hand-taught
classes of `examples/taught-2026-09-16/` plus the shipped vocabulary. A repair counts only when the tests
that rejected the code accept it.

## What happened

**On ordinary utilities the models were mostly right.** Haiku: 16 of 16 correct. qwen3.5:4b: 15 of 16. That
alone should temper the pitch — a capable model writing a small, well-specified function usually gets it
right, and there is no bug to repair.

**On boundary-heavy work the small models broke often**, and the breakages are the interesting part. The
capable one did not break at all.

| writer | wrote | broken | fluidfix repaired, verified | refused | wrong |
|---|---|---|---|---|---|
| qwen3.5:4b | 16 | 3 | 0 | 3 | 0 |
| phi4-mini | 16 | 5 | 1 | 4 | 0 |
| gemma3:4b | 16 | 5 | 0 | 5 | 0 |
| **Claude Haiku** | 16 | **0** | — | — | — |

Haiku wrote both sets without a single failure: 32 implementations, 32 passing their hidden tests, including
the ceiling, the half-open interval and the nearest-rank percentile. Every bug measured here was written by
a 4-billion-parameter local model.

The one repair, free and byte-verified, was a flipped comparison in an insertion loop:

```
- if items[i] > value:
+ if items[i] < value:
```

## Why the other twelve were refused

Reading them one by one, the twelve fall into three groups, and only the first is the kind of fault this
vocabulary is built for:

- **One-line token slips (3).** Two writers ended a truncation with `+ '...'` where the spec wanted the
  ellipsis as a separate word, and one built windows with `range(0, n, size)` instead of
  `range(n - size + 1)`. These are single-line rewrites. They are outside the five taught classes, but they
  are exactly the sort of thing one worked example would add.
- **Insertions, which a line-rewriting vocabulary cannot express at all (3).** Two used `ceil` without
  importing it; one mutated a list and forgot to return it. The fix is a line that is not there, and every
  act in the vocabulary transforms a line that is.
- **Structural, wrong-algorithm faults (6).** A retry schedule that returns scalars instead of a list, a
  countdown that prints instead of returning, two line-wrapping loops with the wrong accumulation. No
  single-line transform reaches these; they need a model or a person.

## So, honestly

**It repairs the mechanical subset of model bugs, and only that.** One of thirteen out of the box; perhaps
four of thirteen if the three token slips were taught, which is one afternoon's work. The remaining nine
were never in reach of a line-transform vocabulary and it refused every one of them rather than guessing.

**Zero wrong repairs, again.** That is the number that transfers: across 240 generated bugs, 22 real-repo
mutants and these 13 model-written faults, the tool has not once shipped a repair that the judging tests
rejected, and every refusal named what it tried.

**The pitch that survives this measurement** is not "it cleans up after your AI". It is: when a test goes
red in a large repository, this finds the mechanical fault for free and refuses honestly on the rest — and
mechanical faults come from typos, refactors, merges and off-by-ones at least as often as from a model.

## Not claimed

- Four writers, thirty-two implementations, thirteen bugs. This is a probe, not a benchmark.
- No frontier model through an API wrote any of this code. The strongest writer available, Haiku through a
  sandboxed subagent, made no mistakes at all on either set, so there is no evidence here about what a
  frontier model's bugs look like — only about small local models.
- The classification of the twelve refusals into three groups is my reading of the code, not a measurement.
