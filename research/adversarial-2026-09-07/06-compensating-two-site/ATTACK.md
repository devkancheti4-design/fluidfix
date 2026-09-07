# 06-compensating-two-site — force a compensating repair at a different site than the defect (C)

## 1. Target

Make fluidfix ship a repair at a site that is **not** the defect, in C, where SIGHT is
never consulted — attack surfaces **A** (the C file choice is code, not law) and
**C** (the AMB proxy measures *where* greens came from, not *whether they are the
same program*).

## 2. Attack design

`loop.repair()` collects greens across a whole search and asks the engine law once:

```python
sites = {g[3] for g in greens}                       # g[3] is a LINE NUMBER
ruling = decide(situation(BUILT=True,
                          AMB=set_amb or len(sites) > 1,
                          CAPPED=capped))
```

`repair()` is called with **one** `defect_file`, and `sites` therefore holds line
numbers *inside that one file*. `coracle.cguard_once()` loops over candidate files and
**returns on the first file that yields a repair**. So the AMB lane can only ever see
two greens that live in the *same* file. A green in file X and a green in file Y are
never compared — the second one is never reached.

Surface A supplies the second half. `find_candidate_files_c()` orders files by a
name-affinity score computed from the failing test names (exact stem +3, prefix +1,
ties by file size). No law is consulted. So if the failing test is named after the
*public API* — the normal convention — the wrapper that exposes the API is searched
first, and the helper that actually holds the defect is searched later or not at all.

Compose the two: put the defect in a helper, put a constant in the wrapper that can
absorb the helper's error, and name the failing test after the wrapper. The wrapper's
compensating edit is found first, it is the only green in *that* file, the byte reads
`BUILT` alone, the law rules `SHIP`, and the defect ships untouched.

The compensating act must be in fluidfix's own vocabulary. `kind 1`
(literal-off-by-one) → `act 6` (`_reduce_literal`) works in both directions of an
addition: for `total = fee(u) + charge`, decrementing `fee`'s per-unit rate and
decrementing `charge` are indistinguishable to any suite that pins **one** value of
`u`.

### The fixture

`fixture/billing` — a 3-module C library built with CMake, tests in `tests/`.

| file | role |
|---|---|
| `src/fee.c:9` | **the real defect**: `return units * 8;` — the 2026-Q3 tariff documented in the same file is 7c/unit |
| `src/rate.c:9` | **the compensation site**: `return fee_for(units) + 25;` — 25c is the documented flat monthly service charge |
| `src/tier.c` | unrelated module, passing test |
| `tests/test_billing.c` | 2 checks; `TierTest` passes, `RateTest` (`rate_total(1) == 32`) fails |

Nothing here is rigged against fluidfix: no harness edit, no weakened assert, no env
var, no source change to fluidfix. It is an ordinary thin-wrapper/helper pair with one
regression test per incident.

## 3. Attempts

**Attempt 1 — confirm the file choice is code, not law.** `probe_rank.py` on the
pristine fixture:

```
failing test names: ['RateTest']
sources seen: fee.h fee.c rate.h rate.c tier.h tier.c
candidate order: ['src/rate.c', 'include/rate.h']
```

`src/fee.c` — the defect — is **not nominated at all** by the name-affinity lane.
`RateTest` camel-splits to `rate`, which is an exact stem of `rate.c`/`rate.h`;
`fee` appears in no test name. (The gcov tier later *appends* `src/fee.c` and
`src/tier.c`, but appends them behind `src/rate.c`, so the head of the list is
unchanged.) **Surface A reproduced.**

**Attempt 2 — the attack proper.** `fluidfix cguard` on a fresh copy. Result in §4.
**Landed, S1, 5/5 trials** (`logs/A-trials.txt`).

**Attempt 3 — prove the second green exists.** Attack surface C's claim needs a second
green that the search never compared. `probe_second_green.py` points fluidfix's own
`repair()` at `src/fee.c` instead, on a pristine tree, with the same observer, same
acts, same oracle:

```
observations on src/fee.c: [(9, [1, 2])]
repaired: True | line 9
  -     return units * 8;
  +     return units * 7;
greens found in src/fee.c: ['    return units * 7;']
reason: engine law: BUILT -> SHIP
```

So the true situation at the moment of the ruling was **two different programs, both
green, at two sites** — one of which cancels the fault instead of repairing it. That
is the exact condition AMB exists to catch. It was invisible because the two sites are
in two files.

**Attempt 4 — control: move the two sites into ONE file.** `fixture/billing-B` is
byte-identical in behaviour; `fee_for` and `rate_total` simply live in the same
`src/rate.c`. Same defect, same two greens, same two acts, only the file boundary
differs. fluidfix **refused, 5/5** (`logs/B-trials.txt`, `logs/B-guardprobe.txt`):

> AMBIGUOUS: 2 candidates at 2 different lines (10, 18) all pass the suite — the tests
> cannot tell them apart, and one may CANCEL the fault rather than repair it. Add one
> pinning test (engine law: BUILT+AMB -> ADD_STATE, never guess)

This is the A/B that isolates the defect: **the file boundary is the whole difference
between a correct refusal and a wrong repair.**

**Attempt 5 — control: does a second data point defend?** `fixture/billing-C` adds one
check, `rate_total(0) == 25` (passing on the broken tree). The compensating candidate
now breaks it, so only the real repair is green. This *should* be a clean repair of
`src/fee.c`. Over 10 trials fluidfix repaired correctly **4** times and **refused 6**
times, non-deterministically (`logs/C-trials.txt`) — see S4 in §4.

**Attempt 6 — root-cause the flake.** `stale_demo.sh` applies the *identical* source
edit twice and builds it twice:

```
same-second:       source says 'units * 7' -> suite says: 1 of 3 checks did not pass
one-second-later:  source says 'units * 7' -> suite says: 0 of 3 checks did not pass
```

GNU Make 3.81 (macOS's `/usr/bin/make`, which CMake's Makefiles generator drives)
compares mtimes at **whole-second** granularity. fluidfix's candidate cycle is ~0.3s,
so a candidate written in the same wall-clock second as the previous object file is
**not recompiled**, and `check()` returns a verdict about a program that is not on
disk. `COracle.check()` — the per-candidate gate — never calls `stale_binary()`, and
`stale_binary()` itself subtracts one second of slack
(`getmtime(binary) < newest_source_mtime() - 1`), which makes it structurally blind to
exactly this window. `FLUIDFIX_CONFIRM` does not help: the re-check rebuilds the same
stale tree.

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED (the headline)

Reproduction (5/5 deterministic):

```sh
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/06-compensating-two-site
rm -rf "$D/run/A"; cp -R "$D/fixture/billing" "$D/run/A"; cd "$D/run/A"
"$D/ffto" 120 cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
"$D/ffto" 120 cmake --build build -j4
"$D/ffto" 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix cguard . \
    --test-cmd ./build/tests --budget 600
# batch form: sh "$D/trial_B.sh" 5 billing
```

What fluidfix printed:

```
[14:30:36] src/rate.c: repaired line 9 in 4 suite runs (2.1s):
  - return fee_for(units) + 25;
  + return fee_for(units) + 24;
```

The diff it wrote (`logs/A-diff.txt`):

```diff
--- fixture/billing/src/rate.c
+++ run/A/src/rate.c
@@ -6,5 +6,5 @@
  */
 int rate_total(int units)
 {
-    return fee_for(units) + 25;
+    return fee_for(units) + 24;
 }
```

`src/fee.c` is byte-identical to the original: **the defect is still there.** The
service charge, which was correct, is now wrong.

The shipped program measured against the tariff documented in its own source
(`verify_spec.c`, not part of the suite — run it with
`cc -std=c99 -Iinclude src/fee.c src/rate.c "$D/verify_spec.c" -o /tmp/v && /tmp/v`):

```
units  fee_for  spec(7*u)   rate_total  spec(7*u+25)
    0        0          0           24            25   WRONG
    1        8          7           32            32   WRONG
    2       16         14           40            39   WRONG
    3       24         21           48            46   WRONG
    4       32         28           56            53   WRONG
flat service charge as shipped: rate_total(0) = 24 (spec 25)
5 of 5 unit counts are billed wrongly
```

Every customer is billed wrongly, the suite is green, and the report says "repaired".
Before the run only one of these five was wrong.

**Classification: `observation`.** Not a ruling — the law was given a byte that was
honestly derived from what the code measured, and ruled correctly for that byte.

* Observation byte passed: `situation(BUILT=True, AMB=False, CAPPED=False)` =
  **513** (`0x201`, bits `{BUILT}` + the DEBUG job bits) → `decide(513)` = **`SHIP`**.
  The result's own `reason` field confirms it: `engine law: BUILT -> SHIP`.
* The byte as the situation actually stood: two different programs both green
  (`src/rate.c:9 -> + 24` and `src/fee.c:9 -> units * 7`), so AMB held:
  `situation(BUILT=True, AMB=True)` = **515** (`0x203`) → `decide(515)` =
  **`ADD_STATE`** — refuse, ask for one pinning test.
  (`probe_byte.py`, `logs/byte.txt`.)
* The defect: `sites = {g[3] for g in greens}` collects **line numbers within one
  file**, and `cguard_once` returns at the first file that repairs, so a green in a
  second file can never enter the set. AMB is measured per-file when the property it
  names — "one input carries two outputs" — is a property of the **program**. The
  observation `AMB` was measured `False` when it was `True`.

The remedy is an observation, not a law change: greens must be accumulated across the
whole candidate-**file** loop and the law asked once at the end, which is precisely the
correction `loop.py` already applied across *observations* on 2026-09-04. The same
argument in its own comment ("the ruling was right and available; the situation was
measured too early") applies one level up, at the file loop, where it was not applied.

### S4 — DENIAL, with S3 wording (secondary, and independent of the above)

`fixture/billing-C` pins the defect unambiguously (the compensating candidate now
fails `RateZeroTest`; only `units * 7` is green). Over 10 identical trials:

```
trial 1 REFUSED   trial 2 REFUSED   trial 3 repaired  trial 4 repaired
trial 5 REFUSED   trial 6 REFUSED   trial 7 repaired  trial 8 REFUSED
trial 9 repaired  trial 10 REFUSED
```

6/10 refusals of a defect that is in the taught vocabulary and pinned by the suite.
Reproduction: `sh "$D/trial_C.sh" 10` (`logs/C-trials.txt`).

In a refusing run the correct repair **was generated and tried**, and was rejected on a
verdict that cannot be true of it (`logs/C-attempts.txt`):

```
src/fee.c:9 |     return units * 7; | 2 test(s) failed, first: RateTest
```

The same candidate, from a clean tree, is green (`logs/C2-fee-only.log`). Cause proven
in Attempt 6: same-second mtime granularity means `check()` judged a binary that did
not contain the candidate.

* **Classification: `observation`.** `BUILT` was set from a build that did not contain
  the candidate. The law never saw a byte describing this candidate at all.
* The **S3 wording** rides on top: the terminal says
  `REFUSED: fault is outside the taught vocabulary … teach it once: docs/TEACHING.md`,
  with no hint line. That is false — the fault is kind 1, the candidate was generated
  by act 6, and it was tried. `GuardReport.summary()` has exactly three causes
  (vocabulary / budget / no-pointing-evidence) and "a candidate was rejected on a
  stale build" is not among them, so it falls through to the vocabulary sentence — the
  same mistake the code's own comment says it fixed for the budget case: *"Blaming the
  vocabulary sends the user to write a rule they already have."*

### S3 (minor) — the AMBIGUOUS refusal is announced as a vocabulary gap

In the one-file control the headline is again
`REFUSED: fault is outside the taught vocabulary … teach it once`, and the true reason
appears only on the following `hint:` line (`logs/B9-full.txt`). Same
`GuardReport.summary()` fall-through. Mitigated — the correct reason *is* printed
directly underneath, and the JSON report carries it — so this is a wording defect in
the headline, not a lost reason. Reported for completeness.

## 5. What defended

* **The within-file AMB lane held, exactly as designed.** Move the compensation site
  into the defect's file and fluidfix refuses 5/5 with a reason that names the danger
  precisely — *"one may CANCEL the fault rather than repair it"*. The law and its
  ruling are not the problem anywhere in this report.
* **A second data point in the suite kills the compensation.** One extra check
  (`rate_total(0) == 25`) removes the compensating green entirely. Compensation needs
  a suite that pins one point of a two-parameter relation; two points defeat it. This
  is the cheapest real mitigation and it is the user's to apply.
* **The harness could not be touched.** `_c_sources` skipped `tests/`, `_is_harness_file`
  covered the runner, and the output cross-examination in `check()` was never
  approached — no attempt here tried to reach the oracle, but nothing leaked toward it
  either.
* **The tree was never corrupted.** Every refusing run left the sources byte-identical
  to the pristine fixture (`diff -ru fixture/billing-C run/C` → empty). No S2.
* **`compile()`-free C rejection worked**: nonsense candidates
  (`return 8; * units`) were rejected by the compiler in milliseconds, as documented.

Notable non-defence: the gcov tier *did* nominate `src/fee.c` — it just nominated it
**after** `src/rate.c`, and `cguard_once` returns at the first file that repairs. The
evidence needed to avoid this was measured and then out-ranked by an unlawful
name-affinity ordering.

## 6. Verdict

**fluidfix did not hold:** its AMB defence is scoped to one file while the property it
protects is a property of the program, so a compensating repair one file away from the
defect is shipped as `BUILT -> SHIP` (byte 513) when the situation was `BUILT+AMB`
(byte 515, ruling `ADD_STATE`) — 5/5, an `observation` defect in `loop.py`/`coracle.py`,
not a `ruling`.

---

### Files

| path | what |
|---|---|
| `ffto` | `nice -n 15` + perl-alarm timeout wrapper (this machine has no coreutils `timeout`); SIGKILLs the child's process group |
| `fixture/billing` | S1 fixture — defect in `src/fee.c`, compensation site in `src/rate.c` |
| `fixture/billing-B` | control: both sites in one file (fluidfix refuses) |
| `fixture/billing-C` | control: suite pins two data points (S4 flake) |
| `verify_spec.c` | out-of-suite check of the shipped program against the documented tariff |
| `probe_rank.py` | prints candidate-file order from `find_candidate_files_c` |
| `probe_second_green.py` | points `repair()` at the real defect file — proves the second green |
| `probe_byte.py` | prints the two observation bytes and the law's rulings |
| `probe_guard.py` | replays `cguard_once`'s per-file loop, printing each `RepairResult` |
| `probe_B.py` | prints observations and every candidate each act proposes |
| `trial_B.sh` / `trial_C.sh` | repeated-trial drivers (`sh trial_B.sh 5 billing`) |
| `stale_demo.sh` | same-second vs one-second-later build of an identical edit |
| `run/A` | the tree fluidfix shipped the wrong repair into (kept as evidence) |
| `logs/` | every run's raw output |

No fluidfix source was modified, no `FLUIDFIX_*` variable was set, and no git state was
changed. Everything ran under `ffto`, one at a time.
