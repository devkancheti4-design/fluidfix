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

## 5. What is not claimed

- These are five incidents on two repositories, not a benchmark.
- The memory was measured on exact-signature recall and one class transfer. It has not been measured against
  a drifting repository, nor against a signature that recurs with a *different* cause — the case where a
  confident memory would be confidently wrong. The gate abstains on absence, not on staleness.
- The fan-out was capped at 6–8 territories by hand. A repository with the fault outside that cap is back to
  a ranking problem.
- Nothing here changes the product. It is a harness around the shipped guard.
