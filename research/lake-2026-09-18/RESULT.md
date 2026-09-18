# Many small fluidfixes, one judge — measured 2026-09-18

The claim under test, in the user's words: *fluidfix is small, so we can use as many as we want.* The tool is
small — **5,580 lines across 18 modules, 258 KB, zero runtime dependencies**. What is not free is the target's
test suite, which every guard pays for once per candidate. So the question is not whether many copies fit in
memory; it is whether splitting the search across many copies buys anything the single guard cannot get.

Everything below runs the product's own code: the same packet builder, mechanical observer, ranking, repair
loop, six laws, byte-exact rollback, and the repository's own suite as the only judge. The harnesses in this
directory decide only **what each guard is allowed to look at** and **who listens to the answers**. No product
change was made for these runs.

Source tree under test: `4ea3220` plus the seven fixes from 2026-09-16 (committed `651b30d`).
Dictionary: `examples/taught-2026-09-16/rules_session.py`, five classes taught by hand from one example each.

## 1. One fault, six ways of looking for it

The fault: `rich/table.py:638`, `last_column = column_index == len(self.columns) - 1` with the `- 1` deleted.
It is in the taught vocabulary. The single guard could never repair it: its file ranking never opened
`table.py` at all, at any budget.

| configuration | fluidfixes | wall | suite runs by the winner | outcome |
|---|---|---|---|---|
| one guard, taught dictionary, 900 s budget | 1 | 904 s | – | **refused** — `table.py` never opened |
| lake, one guard per file, capped view | 16 | 277 s | – | **refused** — fault outside each guard's sampled lines |
| lake, one guard per file, full sight | 16 | 312 s | 117 | exact |
| that winning guard, alone | 1 | 277 s | 117 | exact |
| lake at finer grain: one guard per line range | 4 | 237 s | 59 | exact |
| **router fused into each guard: one file, one class** | 13 | **36 s** | **8** | exact |

Two things are visible in that table. The single guard's failure is a *ranking* failure, and a fan-out fixes
it by covering instead of ranking. And the cost of the winner is set by how much it is allowed to look at:
117 suite runs over a whole file, 59 over a quarter of it, 8 when the router hands it one class as well.

## 2. A fan-out must cover, not rank

The first fan-out refused because each guard read a capped view of its own file (110 of `table.py`'s 294
executed lines, spread-sampled; line 638 fell outside). A guard that owns one territory can afford to read
all of it — that is the point of sharding by file.

The second refused because the plan gave each territory only its three *scarcest* classes, and the answer was
class 7. Pruning a fan-out by a heuristic reintroduces exactly the failure the fan-out exists to remove. The
cold plan now dispatches every class each territory can exhibit.

Both were harness errors, found and fixed here, and both are worth stating because they are the two ways a
"many small workers" design quietly stops covering what it claims to cover.

## 3. The recursive model: the same organ at every level

Fused from two of the author's repositories, both AGPL-3.0, both carrying the same memory core (`life.py`,
sha256-identical in each; vendored here unmodified with attribution):

- **github.com/devkancheti4-design/life-debugger** — the ladder and the memory: the cheap thing first, the
  memory second, an expensive call only for the genuinely new, and the answer kept afterwards. `recall()` on
  an absent key returns `None`: abstention, not a guess.
- **github.com/devkancheti4-design/living-fused** — the confidence gate used as a **router**: what the memory
  knows confidently is answered with zero expensive calls, and the expensive calls are **counted**, so a
  saving is a fact rather than a claim.

Here the expensive call is a dispatched fluidfix and the suite runs it pays for.

- **Level 0**, inside one fluidfix: the taught vocabulary proposes, the suite judges, a refusal is reported.
- **Level 1**, the judge over N fluidfixes: `Life` keyed by the failure signature → `territory|class`, read
  through the gate `w = t/(t+C)`. Above the gate it dispatches one guard; absent, it abstains into the
  fan-out and learns the winner.
- **Level 2**, the same organ at a coarser key: `winners → class`. A signature never seen before still
  inherits the fan-out *order* from it, so the lesson crosses repositories even though the signature does not.
- **Level 3** would key the same table by repository. Nothing in the structure changes; only the key does.

### Measured

| incident | memory | fluidfixes dispatched | suite runs paid | winner's runs | wall | cpu-sum | verdict |
|---|---|---|---|---|---|---|---|
| **cold** — rich `table.py`, first sight | confidence 0.000 → abstain | 45 | 222 | 8 | 112.6 s | 4,378.6 s | exact |
| **warm** — the same failure again | confidence 0.800 → recall | **1** | **8** | 8 | **27.4 s** | **27.3 s** | exact |
| **transfer** — arrow `locales.py`, new signature | 0.000, but class 7 answered before | 23 | 25 | 2 | 75.4 s | 1,373.4 s | exact |

Cold to warm on the identical failure: **45 fluidfixes → 1, 222 suite runs → 8, 4,379 CPU-seconds → 27.**
The memory after all three incidents is **6 rows, 419 bytes**, and its sha is reproducible.

The transfer row is the interesting one. Arrow's `locales.py` fault is the case the single guard *found and
held* at 838 s under a capped view, and the kind-routed version shipped at 931 s. With the class carried over
from an unrelated repository, the winner needed **2 suite runs** and the whole incident took **75 s**.

## 4. Where it stops being free

A dispatched fluidfix is cheap to start and costs one suite run per candidate. On one 12-core machine the
cold fan-out of 45 guards spent 4,379 CPU-seconds to save a 904-second failure, and the winning guard was
only ~12% slower under 16-way contention than alone. The ceiling is the suite and the cores, not the tool.
Measured directly: a synthetic package (40 modules, 40 tests, green suite
0.47 s) cloned N times, the same fault in each, all N guards launched at once on 12 cores.

| simultaneous fluidfixes | wall | median guard | slowdown vs one | byte-exact |
|---|---|---|---|---|
| 1 | 4.3 s | 4.3 s | 1.0x | 1/1 |
| 2 | 4.4 s | 4.4 s | 1.0x | 2/2 |
| 4 | 4.6 s | 4.6 s | 1.1x | 4/4 |
| 8 | 6.3 s | 6.3 s | 1.5x | 8/8 |
| 12 | 8.4 s | 8.4 s | 2.0x | 12/12 |
| 16 | 10.5 s | 10.5 s | 2.4x | 16/16 |
| 24 | 15.7 s | 15.7 s | 3.7x | 24/24 |
| 32 | 22.4 s | 22.0 s | 5.1x | 32/32 |

Up to four guards an extra copy is free. At twelve, one per core, each guard takes twice as long as it would
alone. At thirty-two the slowdown is 5.1x — close to guards-per-core, which is what it should be when the
suite is the cost and the tool is not. Every guard repaired byte-exactly at every width: crowding them slows
them, it does not make them wrong. So "as many as we want" is true of correctness and of memory, and bounded
by cores and suite time for latency.

## 4b. Keying the memory on the shape, not the signature

Section 3's memory is keyed by the failure signature, so it only ever helps the *same incident* recurring —
an exact-key lookup, and worth naming as one. The part of fluidfix that generalises is the shape: a class is
a signal plus a transform, so it fires on lines it has never seen. `staged.py` puts the shape in the memory
and dispatches in two waves: **wave 1** is the remembered class across only the territories that can exhibit
it; **wave 2** is every remaining pair. A wave-1 miss widens, so coverage is never lost.

| incident | shape memory | wave 1 | dispatched | suite runs | wall | verdict |
|---|---|---|---|---|---|---|
| rich `table.py`, cold | empty | — | 45 of 45 | 313 | 112.6 s | exact, learns `kind:7` |
| **arrow `locales.py`** — new repo, file, line and test | `kind:7` | **1** | **1 of 16** | **2** | **31.7 s** | **exact** |
| rich `measure.py`, a different class | `kind:7` | 3, missed | 45 of 45 | 527 | 159.6 s | refused |

The middle row is the point. Its signature had never been seen, so a signature-keyed memory offers nothing;
the same fault cost 23 dispatches and 75.4 s in §3, 931 s under kind-routing alone, and was *held unproven*
by a single guard at 838 s. Keyed by shape it is **one fluidfix and two suite runs**. The 45-to-1 collapse
survives the move from recall to generalisation, which is what a lookup table cannot do.

The third row prices both failure modes honestly. A wrong shape guess costs its wave: 3 fluidfixes and 23
suite runs before widening — about 5% of that incident's total. The refusal, though, is not the memory's
fault: the territory cap of six excluded `rich/measure.py`, so the faulty file was never dispatched in
either wave. The same fault repairs in 701 s when a single guard is pointed at the whole repository (§6 of
the 2026-09-16 study). A cap that hides the fault is still a ranking problem wearing a fan-out's clothes.

## 4c. Not waves — a net that grows from the work

Waves are a plan made before any work is done. A net instead grows, and the law already says in which
direction: a node that comes back **REFUTED** means *not here*, so grow wider; a node that was **CAPPED**
means *here but unproven*, so grow deeper by splitting its line range. Each node is one fluidfix over
(territory, class, line range), and the first green stops all growth (`net.py`).

| incident | search | nodes | suite runs | wall | verdict |
|---|---|---|---|---|---|
| rich `measure.py` (class 6) | fixed waves, 6 territories | 45 | 527 | 159.6 s | **refused** — the cap hid the file |
| rich `measure.py` | net, cold | 129 of a possible 161 | 908 | 625.7 s | exact |
| rich `measure.py` | net, shape known | **13** | **62** | **47.6 s** | exact |
| rich `table.py` (class 7) | fixed waves, cold | 45 | 313 | 112.6 s | exact |
| rich `table.py` | net, cold | 60 of 164 | 656 | 482.2 s | exact |
| arrow `locales.py` (class 7) | net, shape known | **1** of 19 | **2** | **33.3 s** | exact |

Three things fall out of that table.

**Growth buys coverage and costs time.** Where the fixed plan happened to contain the answer, the net is
four times slower (60 nodes against 45, 482 s against 113). Where it did not, the net is the only one that
finds the fault at all. That is the trade you get for growth driven by refusals instead of a plan fixed in
advance.

**A remembered shape is worth what its scarcity is worth.** Arrow's `len(x) - 1` class matched exactly one
of ten territories, so the memory took the search to one node and two suite runs. Rich's `if x:` class
matches twelve of fifty-four, so the same memory narrows 161 pairs to about twelve — a tenfold saving, not a
thousandfold one. Teaching buys a class; scarcity decides whether that class is one place or a dozen.

**The growth rule has to spend the memory correctly.** The first warm run behaved exactly like a cold one
(the same 129-node crawl) because a refusal opened *other classes in the same territory* before trying the
remembered class elsewhere. A remembered class is evidence about the class, not about the territory, so a
refusal on it now moves territory first. That one change took the warm search from 129 nodes to 13.

## 5. What is not claimed

- These are five incidents on two repositories, not a benchmark.
- The shape-keyed memory was measured on one class (`kind:7`) across two repositories, and the miss
  case on one other class. The memory holds one shape here; nothing says how it behaves when a dozen
  classes compete for wave 1.
- The signature-keyed memory was measured on exact recall and one class transfer. It has not been measured against
  a drifting repository, nor against a signature that recurs with a *different* cause — the case where a
  confident memory would be confidently wrong. The gate abstains on absence, not on staleness.
- The fan-out in §3 and §4b was capped at 6–8 territories by hand, and §4c is what happens when that cap
  is removed: the net reaches the fault, at four times the cost when the cap was not the problem.
- The net was measured on three incidents in two repositories, with one class remembered at a time.
  Nothing here says how the growth rule behaves when several classes compete for the frontier.
- Nothing here changes the product. It is a harness around the shipped guard.
