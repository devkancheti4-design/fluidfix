# Does the knowledge generalise, and does the free share rise? — measured 2026-09-18

The claim that decides whether this replaces an agent or merely assists one:

> As the vocabulary grows, the share of incidents handled with no model call rises, and what is left for a
> model is only the genuinely open-ended minority.

That claim has a load-bearing half and a decorative one. "It gets better with use" is decorative — any cache
can say it. The load-bearing half is **generalisation**: a taught shape must repair instances it was *never
shown*, or the vocabulary is a lookup table with extra steps and the curve flattens the moment exact lines
stop recurring.

## Method

240 bugs over eight shapes, **every instance distinct** — its own function name, its own variables, its own
literals, its own shell — each with a test that catches it, and each verified to fail before anything runs.
Nothing a shape repairs here was ever shown to it.

Two arms face the same stream. **LINE TABLE** stores the exact broken line against the exact fixed line, one
row per repair, and may only replay a line it has literally stored. **SHAPES** is the vocabulary, judged by
each instance's own test. The curve is drawn over **K, the number of taught classes loaded** — K=0 is the
shipped vocabulary alone; K=4 fills every dictionary slot.

Slots 4 and 5 were written this afternoon from the **edit-budget ladder's own output**
(`../kindof-2026-09-18`), derived from faults small models actually wrote. Slots 6 and 7 are the 2026-09-16
session's classes, unchanged.

## Result

| taught classes | repaired free | line table | rows the table stored |
|---|---|---|---|
| 0 — shipped only | 120 / 240 — **50%** | 41 — 17% | 79 |
| 1 — + mutating-call | 150 / 240 — **62%** | 41 — 17% | 109 |
| 2 — + missing-separator | 180 / 240 — **75%** | 41 — 17% | 113 |
| 3 — + inverted-guard | 210 / 240 — **88%** | 52 — 22% | 132 |
| 4 — + len-as-last-index | 240 / 240 — **100%** | 68 — 28% | 146 |

**Every taught class took its entire share of the stream: 0/30 → 30/30, on instances it had never seen.**
That is the generalisation the thesis needs. A shape is a signal plus a transform, so it matches names,
values and surroundings that were in no example; the table, which can only replay what it stored, reached
28% while holding **146 rows against the vocabulary's four**.

**The two shapes learned this afternoon behaved exactly like the ones taught by hand a fortnight ago.**
`mutating-call` and `missing-separator` were written from what the ladder found in real model-written
faults, and both went 0/30 → 30/30 on code nobody had seen. Knowledge extracted from incidents transfers.

## What this does and does not settle

**Settled: it generalises, and the curve is not a cache's curve.** Four shapes beat 146 stored rows by
72 points. Each class added moves the free share by its full share of the stream, not by a diminishing
fraction, because a shape does not wear out on unseen inputs.

**Not settled, and it is the half the thesis actually turns on: shape coverage of real incidents.** Every
bug in this corpus is one of eight shapes I chose, so "100%" means *100% of bugs whose shape is taught* — it
cannot mean 100% of bugs. The open-ended faults, the ones a model must still write, are by construction
absent here. Whether they are "very few if taught right" in a real repository is not measurable from a
corpus I built; it needs a real incident history.

The nearest real evidence, and it is much weaker: on four real repositories, 22 of 38 live breaks fell
inside the taught vocabulary and 16 did not (`research/llm-fusion-2026-09-16`). That is a 58% shape-coverage
figure on *seeded* faults of shapes chosen in advance, not on a company's actual incidents. It is the number
to replace, not to quote.

**So the honest form of the thesis:** *within* a shape, the vocabulary generalises completely and the free
share rises linearly with teaching, while a table does not. *Across* shapes, nothing here says what fraction
of real incidents are teachable — and that fraction, not the curve, decides whether a model is still needed
for most of the work.

## Not claimed

- 240 generated bugs, eight shapes, one seed. The instances are distinct but they are mine.
- The stream is uniform: 30 of each shape. A real repository's incidents are not uniform, and a shape that
  is scarce pays for its slot far more slowly — measured elsewhere: a class matching one territory of ten
  took a search to a single node, while one matching twelve of fifty-four saved a tenth as much.
- The line-table arm is a fair table, not a strawman: it hits whenever an identical line recurs anywhere.
  It still needed 146 rows to reach 28%.
