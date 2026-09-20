# Do two taught classes connect? — 2026-09-20

Every class in the vocabulary was taught from its own worked example, in isolation. Nothing had ever
handed the net a bug needing two of them at once. The answer, asked directly: **no, and then yes.**

## As it stood: no

`shapes_repair` accepts a candidate only when the WHOLE suite goes green. With two faults present, a
perfectly correct repair for one of them leaves the suite red and is discarded — indistinguishable, to a
boolean runner, from a repair that did nothing. The vocabulary already held both fixes and threw them
both away.

| case | one-shot |
|---|---|
| C one fault, class 7 alone | REPAIRED, 1 run |
| C2 one fault, class 4 alone | REPAIRED, 1 run |
| **A two faults, classes 7 + 4, two lines** | **refused** |
| **B two faults, classes 7 + 4, one line** | **refused** |

## What it takes: a runner that says WHICH tests fail

A correct partial fix has a signature a boolean cannot see — the failing set strictly shrinks and no
passing test starts failing. That is enough to step. Intermediate steps are provisional, never certified;
only the final state is judged by the whole suite going green, and if descent never reaches green every
edit is rolled back and the answer is still refusal.

| case | depth 1 | depth 2 |
|---|---|---|
| C one fault, class 7 | REPAIRED, 2 runs | REPAIRED, 2 runs |
| C2 one fault, class 4 | REPAIRED, 2 runs | REPAIRED, 2 runs |
| A two faults, two lines | **REPAIRED, 6 runs** | REPAIRED, 10 runs |
| B two faults, ONE line | refused | **REPAIRED, 4 runs** |
| D THREE faults, classes 7 + 4 + 6 | **REPAIRED, 11 runs** | REPAIRED, 19 runs |

Depth 1 connects classes **across lines**. Three faults, three classes, eleven suite runs, each step
visible in the failing count: 5 → 4 → 2 → 0.

Two faults on the SAME line need depth 2, because neither single repair changes which tests fail — the
index error and the wrong operator mask each other, so the step has no gradient:

```
return words[len(words)] and fallback        failing [0, 1]
  kind 4  -> words[len(words)] or fallback       failing [0, 1]   no gradient
  kind 7  -> words[len(words) - 1] and fallback  failing [0, 1]   no gradient
  composed -> words[len(words) - 1] or fallback  failing []       green
```

Depth 2 feeds a candidate back through the vocabulary before testing it. Cost is candidates-per-line
squared, and a line yields one to three — but it is not free: A goes 6 → 10 runs and D goes 11 → 19 when
the composition is not needed.

## Does the looser intermediate gate let a wrong fix through? Yes, unless the properties are loaded

The adversarial case is the rich incident reproduced inside a composition: two faults, one of them at a
multiplicative position, and a suite that is WEAK there — it only ever exercises `k = 1`, where
`k * len(x) - 1` and `k * (len(x) - 1)` agree.

| arm | outcome |
|---|---|
| naive class 7, property gate off | green, and **WRONG** — shipped `k * len(items) - 1` |
| naive class 7, property gate on | **refused**, 8 candidates blocked before any suite run |
| placement law, property gate on | green, and **CORRECT** — `k * (len(items) - 1)` |

So descent does not weaken safety. The property gate is what holds it, and the wrong composition is
refused eight times over rather than shipped.

## The flaw this exposed: the gate FAILS OPEN

The first run of that safety test reported `0 blocked` while shipping the wrong fix. The harness had
loaded the class dictionary but not the properties file — they are separate files — so `PROPERTIES` was
empty, every check returned UNPROVEN, every candidate passed, and the gate reported zero refusals while
doing nothing at all.

That is a safety gate that silently no-ops when unconfigured, and it is worse than having no gate,
because the zero looks like a clean bill of health. Two additions:

- `props.classes_without_properties(kinds)` — names the taught classes the gate cannot speak for. Call it
  after loading and say something about what it returns.
- `gate(..., strict=True)` — refuses UNPROVEN as well as REFUTED, for the case where the proof, not the
  suite, is the thing being relied on.

## Honest boundaries

- Descent is **greedy**. It takes the first strictly-improving step it finds, and does not backtrack. A
  bug where the only route to green runs through a step that makes things temporarily worse is out of
  reach.
- Depth 2 is composition of **two** classes on one line. Three on one line is not tested.
- Every case here is a constructed fixture. This says the mechanism connects; it does not say how often
  real multi-fault commits are within reach.
