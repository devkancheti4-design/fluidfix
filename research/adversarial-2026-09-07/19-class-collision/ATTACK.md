# 19-class-collision — two taught classes whose candidate sets contradict

## 1. Target

Two taught fault classes whose signals match the same line and whose appliers
propose contradictory repairs: which one wins, and is that a law ruling or code
order?

## 2. Attack design

The law-research wave established two facts about the class path:

* `loop.py:283` converts the observer's kind list to a **bitmask**
  (`mask = mask_of(k for k in obs.kinds ...)`). A mask has no order, so all
  `n!` orderings of an `n`-kind line collapse to one value.
* `loop.py:297` then emits with `kind_of(EMIT(mask))` — `EMIT` is the lowest
  set bit, so classes are tried in **ascending kind-id order**, i.e. the number
  the dictionary author happened to type in `register()`.

The attack turns that into a wrong shipped repair by attacking the *other* end
of the loop at the same time. `loop.py:218` computes AMB as
`set_amb or len(sites) > 1`:

* `set_amb` = two greens inside **one** candidate set;
* `sites > 1` = greens at **different lines**.

Two taught classes colliding on **one** line produce two greens at **one** line
from **two** candidate sets — neither disjunct fires. AMB is measured 0, the law
rules SHIP, and `_rule` ships `greens[0]`, the first green found. "First" is
decided entirely by the ascending kind id.

Prediction: the same repo, the same suite, the same two candidate strings, the
same observation byte — and a **different program on disk** depending only on
which class was numbered 4 and which 5. If that reproduces, the tie-break
between two colliding classes is not a ruling; it is `register()` numbering.

Fixture (`fixtures/collide/`): `pricing.py` computes
`price = gross_rate_for(region) * units` where the intended program is
`net_rate_for(region) * units` (`pricing.correct.py`). Constants are chosen so
that a *second*, genuinely different program also greens the one test
(`5.0 * 4 / VAT` with `VAT = 2.5` == `2.0 * 4` == `8.0`). Two dictionary
classes are taught, one for each program, from plausible separate incidents.

## 3. Attempts

Every run: `nice -n 15` plus a perl-alarm timeout wrapper (`run.sh`; this host
has no coreutils `timeout`), one at a time, on a fresh copy of the fixture.

### Attempt 1 — arrangement A: `vat-not-applied` = kind 4, `wrong-rate-helper` = kind 5

**Landed (S1).** `logs/A_vat4_net5.log`. fluidfix wrote the *wrong* program to
disk and reported `"repaired": true`, `"ambiguous": false`,
`"reason": "engine law: BUILT -> SHIP"` — while its own `greens` field in the
same JSON lists **both** programs.

### Attempt 2 — arrangement B: the identical two classes with the kind numbers swapped

**Landed (proves the mechanism).** `logs/B_net4_vat5.log`. Nothing changed but
the two integers in `register()`. Same file, same suite, same two candidates,
same `acts_tried: [6, 6, 6, 9, 10]`, same `suite_runs: 9`, same
`"reason": "engine law: BUILT -> SHIP"`, same `"ambiguous": false` — and the
*other* program on disk (this time the correct one).

### Attempt 3 — arrangement C (control): kind numbers as in A, `register()` calls in the opposite order in the file

**Ships exactly what A shipped.** `logs/C_order_swapped.log`. So the tie-break
is not file order, not registration order, not `dict` insertion order — it is
the kind **number**.

### Attempt 4 — arrangement D (control): the same two repairs taught as ONE class

**Defence held.** `logs/D_merged_one_class.log`. One `register()` at kind 4
whose applier returns both candidates. `greens` is the byte-identical pair of
strings from attempt 1, and fluidfix refuses:

> `AMBIGUOUS: 2 candidates at 1 different lines (15) all pass the suite — the
> tests cannot tell them apart, and one may CANCEL the fault rather than repair
> it. Add one pinning test (engine law: BUILT+AMB -> ADD_STATE, never guess)`

exit 2, tree byte-identical. This is the sharpest statement of the defect:
**identical `greens` lists, opposite outcomes, decided by how many `register()`
calls the two repairs were spread across.**

### Attempt 5 — same-kind collision: two dictionaries both claiming kind 4

**Not a finding, but a documented hazard with an asymmetric guardrail.**
`logs/E_same_kind_kinds.log`. A personal dictionary that loads a team
dictionary and also picks kind 4 silently erases the team class:
`fluidfix kinds` shows kind 4 as the personal class and 5–7 free, with no
warning — `register()` warns only when `kind in SHIPPED_KINDS`
(`acts.py:339`), never for user kinds 4–7. The CLI line
`dictionary ...: 1 fault class(es) registered` is truthful (it counts *new*
kinds) but reads as success. `docs/TEACHING.md` calls this out explicitly
("Registering an occupied kind **replaces** it… how two dictionary files
collide accidentally") and has a troubleshooting row for it, so I am reporting
it as a hazard, not as a successful attack.

Incidental: `__file__` is not bound inside a dictionary file
(`load_dictionary` execs with `ns = {"register", "re", "SpanEdit"}`,
`acts.py:359`), so a dictionary cannot locate a sibling dictionary by path.
Cosmetic; noted, not claimed.

### Attempt 6 — does the marketed guard path do the same?

**Yes, and reports less.** `logs/A_guard.log`. `fluidfix guard` on arrangement
A prints:

```
[14:43:03] pricing.py: repaired line 15 in 9 suite runs (3.5s):
  - price = gross_rate_for(region) * units
  + price = gross_rate_for(region) * units / VAT
```

`.fluidfix/` is left **empty** — the `greens` list that would have shown the
user a second, contradictory passing program exists only in
`repair --json`. On the commit-and-forget path (`--interval --commit`) nothing
records that a second program also greened.

### Attempt 7 — corollary probe: taught classes vs shipped classes

`logs/precedence_probe.log`. On the line
`return max(a, b) if enabled else min(a, b)`, kinds are `[8]` before teaching
and `[4, 8]` after a single `register(4, ...)` — so **any** class taught into
the reserved user slots 4–7 is tried before shipped kinds 8–12
(`minmax-swap`, `flipped-augmented-assign`, `flipped-comparison-direction`,
`reversed-minus-operands`, `flipped-boolean`) on every line where both signals
match, and wins any collision by `greens[0]`. Measured as EMIT order only; I
did not run a suite for this case.

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED

Reproduce:

```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/19-class-collision
./run_case.sh A_vat4_net5 rules_vat4_net5.py      # ships the WRONG program
./run_case.sh B_net4_vat5 rules_net4_vat5.py      # same evidence, ships the right one
./run_case.sh C_order_swapped rules_order_swapped.py   # control: file order is irrelevant
./run_case.sh D_merged_one_class rules_merged.py       # control: one class -> refuses
```

(`run_case.sh` copies the pristine fixture into `runs/<case>/` and invokes
`.venv/bin/fluidfix repair <copy> --file pricing.py --dictionary <copy>/<rules>
--python .venv/bin/python --json` under `run.sh 180`.)

The diff fluidfix wrote in run A:

```diff
--- fixtures/collide/pricing.py
+++ runs/A_vat4_net5/pricing.py
@@ -12,5 +12,5 @@
 def price_for(region, units):
-    price = gross_rate_for(region) * units
+    price = gross_rate_for(region) * units / VAT
     return price
```

The intended program (`pricing.correct.py`) is
`price = net_rate_for(region) * units`. The shipped program passes the suite and
is wrong for every region whose gross/net ratio is not `VAT`; it also leaves
`net_rate_for` and the `NET` table dead. Run B, from the same evidence, wrote:

```diff
-    price = gross_rate_for(region) * units
+    price = net_rate_for(region) * units
```

**Classification: `observation`.**

* **Observation byte passed** (`logs/byte_probe.log`, reproduce with
  `./run.sh 60 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python byte_probe.py`):
  `situation(BUILT=True, AMB=False, CAPPED=False)` = `0x0201` (513) —
  **identical in run A and run B**.
* **Act the law returned:** `decide(0x0201)` = `SHIP`. Correct for that byte.
* **What the law WOULD have ruled on the correct byte:**
  `situation(BUILT=True, AMB=True)` = `0x0203` (515) → `decide` = `ADD_STATE`
  — refuse and ask for one pinning test, which is exactly what arrangement D
  did with the same two greens.

The law was never consulted about class order and never wrong. Two defects in
the body:

1. `loop.py:218` — the AMB proxy measures *where* greens came from
   (`set_amb or len(sites) > 1`), not *whether they are the same program*. Two
   greens at one line from two candidate sets are invisible to both disjuncts,
   so AMB is reported 0 when two different programs passed.
2. `loop.py:283` + `loop.py:297` — the mask erases the observer's ordering
   (all 720 permutations of a six-kind line collapse to one mask value,
   printed in `logs/byte_probe.log`), and `EMIT` re-derives an order from kind
   ids. `Observation.kinds` is contracted as "most specific first"
   (`acts.py:60`, and the `ClaudeObserver` prompt says "most specific first",
   `observers.py:54`), and that priority is discarded before the loop sees it.
   `greens[0]` then makes that discarded-and-reinvented order decide which
   program ships.

The observation that would separate the two: *are the surviving greens the same
program?* A cheap, sound approximation for the Python path is already available
in-process — normalise each green's full file content (e.g. `ast.dump` of
`compile(content, ..., ast.PyCF_ONLY_AST)`) and set `AMB` when two greens
normalise differently, regardless of which candidate set or line they came
from. In arrangement A that flips the byte from `0x0201` to `0x0203` and the
law's existing `ADD_STATE` ruling refuses, with no change to the law.
(Reported only; no `src/` edits were made.)

### S3 — FALSE CONFIDENCE

Same runs. On the `repair --json` path the report asserts
`"ambiguous": false` in the same object whose `"greens"` array holds two
different programs — a claim the run does not support, contradicted by its own
adjacent field. On the `fluidfix guard` path the second green is not reported
at all and `.fluidfix/` is left empty, so a commit-and-forget user has no
record that the repair was a coin flip between two passing programs.
Classification: `wording` for the guard line (the outcome under the current
AMB definition is what the code intends to print), `observation` for the
`"ambiguous": false` field, which is the mis-measured bit itself.

## 5. What defended

* **The single-candidate-set AMB (`set_amb`, `loop.py:400-406`).** Merging the
  two colliding repairs into one taught class (attempt 4) put both greens in
  one candidate set, `set_amb` fired, the law was handed `0x0203`, and fluidfix
  refused with the correct reason and restored the tree byte-exactly. The
  defence exists and works — it is only reachable when the two programs happen
  to be spelled by the same `register()` call.
* **The multi-site AMB (`len(sites) > 1`).** Several earlier fixture drafts
  were killed by it: any variant where the second green landed on a different
  line (e.g. a helper class that also matched the `def` lines) refused as
  AMBIGUOUS instead of shipping. Getting an S1 required forcing both greens
  onto one line.
* **The free syntax rejection and the suite itself** rejected every incidental
  candidate from shipped kind 1 on the constant lines (`logs/A_vat4_net5.log`
  `tried_log`), so the collision was clean.
* **Rollback.** Every refusal left `pricing.py` byte-identical to the pristine
  fixture (`diff -q` in the transcript); no S2 was found.
* **`register()`'s shipped-kind warning** (`acts.py:339`) does fire loudly when
  a dictionary clobbers kinds 0–3 or 8–12. It simply has no counterpart for
  user kinds 4–7.

## 6. Verdict

fluidfix held on integrity and on the law — the engine law ruled correctly on
every byte it was given — but it does **not** hold on class collision: two
taught classes that green one line from two candidate sets are not measured as
ambiguous, and which of the two contradictory programs is written to disk is
decided by the integer the dictionary author typed in `register()`, not by any
ruling (S1, `observation`, `loop.py:218` and `loop.py:283`/`297`).
