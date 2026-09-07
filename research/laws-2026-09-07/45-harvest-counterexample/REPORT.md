# 45-harvest-counterexample

## 1. Target

Prototype the engine law's `HARVEST_COUNTEREXAMPLE` act as a **memory** — keep
rejected candidates as negatives, consult them on a second run of the same
class — and measure the candidate-count and suite-run reduction. Report only:
nothing under `src/` was edited.

## 2. Method

All runs used `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python`, one at a
time, through `./nt.sh SECONDS cmd...` — a `nice -n 15` + `perl alarm` timeout
wrapper written for this machine, which has no coreutils `timeout` (exit 124 on
expiry; every run below exited 0).

Read: `src/fluidfix/loop.py` (whole), `src/fluidfix/guard.py:1-140, 430-624,
690-721`, `src/fluidfix/oracle.py`, `src/fluidfix/localize.py:88-181`,
`src/fluidfix/acts.py:74-120, 300-408`, `src/fluidfix/observers.py:28-42`.

Scripts, all in this directory, all rerunnable:

| script | output | what it measures |
|---|---|---|
| `negatives.py` | — | the prototype: a negatives store + a wrapper over the `candidates` name `loop.py` imported, plus `Counter` (measures `oracle.check` calls and real `python -m pytest` invocations) |
| `bench_crossrun.py N F [--memo]` | `crossrun_base_8x2.out`, `crossrun_memo_8x2.out` | a **second guard run** on the same unrepaired tree |
| `bench_escalate.py [--memo] [--pass0]` | `esc_base.out`, `esc_memo.out`, `esc_pass0.out` | the **escalation pass inside one run**, on a fixture that must still repair |
| `bench_safety.py naive\|fp` | `safety_naive.out`, `safety_fp.out` | whether a memo can lose a repair |
| `cap_effect.py N` | `cap_effect_80.out` | what a read-back of the file fluidfix **already writes** would deliver, with its 64-entry cap intact |
| — | `writeonly_grep.out` | the write-only census |

Instrumentation is by wrapping, never by editing: `oracle.check` / `oracle.run`
are wrapped on the instance, and `fluidfix.loop.candidates` is rebound for the
duration of a run and restored in a `finally`.

Two counters are reported throughout because they are different things:
**candidates adjudicated** = `oracle.check()` calls = one per candidate the
suite judged; **pytest invocations** = real `python -m pytest` subprocesses,
which is the wall-clock cost (`oracle.check` runs the `--lf` fast gate and
then, only if that passes, the full suite; packet building and the `green()`
precondition cost more).

## 3. Findings

### F1. The harvest is written on three paths and read by nothing. The dedupe set is scoped to one `repair()` call.

```
$ grep -rn "tried_log\|tried_more\|rejected_candidates\|last_refusal" src/fluidfix/
src/fluidfix/loop.py:346:                            if len(res.tried_log) < 64:
src/fluidfix/loop.py:351:                                res.tried_more += 1
src/fluidfix/loop.py:407:                    elif len(res.tried_log) < 64:
src/fluidfix/loop.py:412:                        res.tried_more += 1
src/fluidfix/guard.py:518:        attempts += result.tried_log
src/fluidfix/guard.py:598:        attempts += result.tried_log
src/fluidfix/guard.py:719:               "rejected_candidates": report.attempts[:200]},
src/fluidfix/javaoracle.py:214:        attempts += result.tried_log
src/fluidfix/coracle.py:761:        attempts += result.tried_log

$ sed -n "185p;332,334p" src/fluidfix/loop.py
    tried: set[tuple[int, str]] = set()
                    if key in tried:
                    tried.add(key)
```
(full output: `writeonly_grep.out`.) Every occurrence is a write, an append or
a `json.dump`; `report.attempts` is only ever *counted* (`guard.py:104-105`) and
serialised. `tried_more` is written at `loop.py:351/412` and read **nowhere at
all** — not even printed. `loop.py:185` creates the dedupe set inside
`repair()`, so it dies with the call.

### F2. A second guard run on the same unrepaired tree re-tries 100% of what it already refuted; the memo cuts it to zero.

Fixture: two modules carrying a taught class (reserved kind 4) that proposes 8
wrong candidates, plus the shipped literal-off-by-one class — 18 candidates,
none of which can spell the fault. `escalate=False`, so this is purely
run-to-run.

```
$ ./nt.sh 290 .venv/bin/python bench_crossrun.py 8 2            # crossrun_base_8x2.out
[run1] memo=False status=refused seconds=6.4 check=18 pytest=25 attempts=18 persisted_rejects=18 ...
[run2] memo=False status=refused seconds=7.5 check=18 pytest=25 attempts=18 persisted_rejects=18 ...
RESULT memo=False: reduction on the second run — candidates 0.0%, pytest 0.0%, wall -16.8%

$ ./nt.sh 290 .venv/bin/python bench_crossrun.py 8 2 --memo     # crossrun_memo_8x2.out
[run1] memo=True status=refused seconds=7.3 check=18 pytest=25 ... memo_size=18 (+18 this run)
[run2] memo=True status=refused seconds=1.9 check=0 pytest=7 ... memo_skipped=18 memo_size=18
RESULT memo=True: reduction on the second run — candidates 100.0%, pytest 72.0%, wall 73.5%
```
**18 of 18 candidates, 18 of 25 pytest invocations, 5.4 of 7.3 seconds.** The 7
surviving pytest invocations are irreducible under this design: `failing_output`,
the per-file coverage packet builds, and `repair()`'s "is the suite already
green" precondition. They are not candidate work.

### F3. Inside ONE run, the escalation pass re-tries 100% of pass 0's rejections — and the memo removes them without changing the repair.

Fixture (`bench_escalate.py`): a 177-line module whose pass-0 packet is
truncated (`localize.build_packet` `max_lines=110`), so `capped0` holds, the
engine law rules `RAISE_BUDGET` at `guard.py:539`, and escalation rebuilds at
`max_lines=990` — a **superset** of pass 0's stride sample. The true defect is
placed on a line the stride sample drops, so pass 0 *must* refuse and escalation
*must* repair. The 8 decoy lines are inert by construction (`_scratch` is never
read), so no candidate can cancel the fault instead of repairing it.

```
$ ./nt.sh 290 .venv/bin/python bench_escalate.py --pass0        # esc_pass0.out
probe: pass0 packet truncated=True lines=110; escalation packet truncated=False lines=175; lines pass 0 never sees=65
probe: defect at body line 170 (file line 175), in pass-0 packet: False; decoy file lines: [6, 7, 9, 10, 12, 13, 15, 16]
RESULT pass0_only=True ... status=refused
RESULT ... candidates adjudicated (oracle.check)=16 pytest invocations=20 seconds=6.4

$ ./nt.sh 290 .venv/bin/python bench_escalate.py                # esc_base.out
RESULT ... status=repaired file=acc.py lineno=175 new_line='t = t + 1'
RESULT ... candidates adjudicated (oracle.check)=35 pytest invocations=44 seconds=14.6 memo_skipped=0

$ ./nt.sh 290 .venv/bin/python bench_escalate.py --memo         # esc_memo.out
RESULT ... status=repaired file=acc.py lineno=175 new_line='t = t + 1'
RESULT ... candidates adjudicated (oracle.check)=19 pytest invocations=28 seconds=9.3 memo_skipped=16
```

| | pass 0 | escalation | whole run |
|---|---|---|---|
| candidates, shipped | 16 | 19 (35 − 16) | 35 |
| candidates, memo | 16 | **3** | **19** |
| reduction | 0% | **84.2%** | **45.7%** |
| pytest invocations | — | — | 44 → 28 (**−36.4%**) |
| wall seconds | — | — | 14.6 → 9.3 (**−36.3%**) |

`memo_skipped=16` is 100% of pass 0's 16 rejections and 84.2% of the escalation
pass's 19 candidates. **The repair is byte-identical in both runs**: `acc.py`
line 175, `t = t + 1`, verified from disk after the run
(`RESULT ... on-disk line now: 't = t + 1'` in both `esc_base.out` and
`esc_memo.out`).

### F4. The saving is only free if the negatives are scoped to the TREE. A memo without that loses repairs.

A rejection is a fact about the tree it was measured on, not about the
candidate. `bench_safety.py` builds the case: run 1 rejects `LIMIT = 9`
(the test expects 7); the tree then changes and `LIMIT = 9` becomes the repair.

```
$ ./nt.sh 200 .venv/bin/python bench_safety.py naive            # safety_naive.out
[run1] mode=naive expected=7 status=refused check=1 skipped=0 memo=1
[run2] mode=naive expected=9 status=refused check=0 skipped=1 memo=1 new_line=None
VERDICT mode=naive: run1=refused run2=refused — REPAIR LOST to a stale negative

$ ./nt.sh 200 .venv/bin/python bench_safety.py fp               # safety_fp.out
[run1] mode=fp expected=7 fp=2d31ae49a639 status=refused check=1 skipped=0
[run2] mode=fp expected=9 fp=5166310f9b17 status=repaired check=2 skipped=0 new_line='LIMIT = 9'
VERDICT mode=fp: run1=refused run2=repaired — repair still lands
```
The prototype keys every negative on
`(file:site, sha1(candidate text), sha1(tree))`, where the tree hash covers
every source file in the repo. Change one byte anywhere and every negative is
re-tried, so the memo can never turn a repair into a refusal on a tree that
differs from the one the rejection was measured on. Its cost on the fixtures:
`tree_fingerprint cost on this fixture: 0.0001s` (`esc_base.out`). Its cost on
a Box2D-sized tree is **unmeasured**.

### F5. Reading back the file fluidfix ALREADY writes, with no other change, recovers 79% of the saving. The 64-entry cap costs the rest.

`cap_effect.py` builds run 2's memo *only* from `.fluidfix/last_refusal.json`
as `write_refusal` wrote it — 64-entry cap and 200-character truncation intact.

```
$ ./nt.sh 290 .venv/bin/python cap_effect.py 80                 # cap_effect_80.out
[run1] N=80 adjudicated=81 pytest=85 seconds=21.1 attempts=64 persisted=64
[run1] loop.py's 64-entry cap dropped 17 of 81 rejections before they were ever persisted (RepairResult.tried_more)
[run2] memo-from-last_refusal.json ... skipped=64 adjudicated=17 pytest=21 seconds=6.0
RESULT N=80: read-back of the file fluidfix ALREADY writes saves 64 of 81 candidate adjudications (79.0%), 64 of 85 pytest invocations, 15.1s of 21.1s
```
(`entries=81` printed on that line is the store size *after* the run, because
the prototype also memoises the 17 candidates run 2 newly tried; `skipped=64`
is the figure that matters.) So the cap is worth **21% of the achievable
saving at 81 candidates**, and the excess is not merely uncapped-and-unpersisted:
`tried_more` is not written into `last_refusal.json` at all, so nothing
downstream can even learn how many were dropped.

### F6. A fully-memoised refusal currently loses its evidence sentence.

`guard.py` decides the refusal wording from `acts_tried` / `attempts`. Filter
every candidate and both go empty, so the REFUTED hint at `guard.py:617-621`
never fires:

```
[run1] summary: 'REFUSED: fault is outside the taught vocabulary (...). teach it once: docs/TEACHING.md
  (...) 18 candidate(s) were tried and rejected — each is logged with the test that failed it in the
  refusal report.\n  hint: every generated candidate was rejected by the suite
  (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) — ...'
[run2] summary: 'REFUSED: fault is outside the taught vocabulary (...). teach it once: docs/TEACHING.md (...)'
```
(`crossrun_memo_8x2.out`.) The headline stays true, but the second run silently
drops "18 candidate(s) were tried and rejected" and the law citation. The fix is
plumbing, not a decision: a skipped negative must still count into `attempts`
(it already carries its `why`) and into `acts_tried`. Any implementation of this
act must carry it or it trades a speed win for a wording defect.

## 4. Lanes

Engine-law lanes this work **reached**, with where:

- **byte 64, `REFUTED` -> `HARVEST_COUNTEREXAMPLE`** — `guard.py:617-621`, quoted
  verbatim in the baseline refusal hint of F2 run 1. This is the lane under
  test; it is reached on every refusal where any candidate was tried.
- **byte 4/5, `CAPPED(+REFUTED)` -> `RAISE_BUDGET`** — `guard.py:539`, the gate
  that makes F3's escalation pass run at all.
- **byte 1, `BUILT` -> `SHIP`** — `loop.py:217-229`, the repair in F3 and in
  F4's `fp` run 2.

Lanes this work **never reached**: `AMB` (F3's decoys are inert by
construction precisely so that AMB cannot fire — that is target 04/41's
experiment), `HIDDEN` (no flaky suite here — target 05/42), `UNREAD`
(`pytest-cov` is installed), `NOTWIN` and `SELF` (no observation in the body
can set either; targets 09 and 33 cover them). `byte 65 BUILT+REFUTED` is not
constructible from `guard.py`'s two call sites, which pass `REFUTED=acts0`
without `BUILT`.

The lane the *body* never consults is the point of this target: the law's
`HARVEST_COUNTEREXAMPLE` ruling fires, the harvest it names is written to disk,
and no code path reads it. The observation needed to close it is not a new
measurement — it already exists as `RepairResult.tried_log`. What is missing is
a *lookup* before `loop.py:305`'s candidate loop and a tree fingerprint to scope
it.

## 5. Potential

Measured on the fixtures in this directory, with a repair required to still
land unchanged in the escalation case:

| where | shipped | with negatives | saving |
|---|---|---|---|
| second guard run, same tree, refusal (F2) | 18 candidates / 25 pytest / 7.5s | 0 / 7 / 1.9s | **100% of candidates, 72% of pytest, 73.5% of wall** |
| escalation pass inside one run (F3) | 19 candidates | 3 | **84.2%** |
| that whole run, repair required (F3) | 35 / 44 / 14.6s | 19 / 28 / 9.3s | **45.7% / 36.4% / 36.3%** |
| read-back of today's `last_refusal.json`, no other change (F5) | 81 / 85 / 21.1s | 17 / 21 / 6.0s | **79.0% / 75.3% / 71.6%** |
| lifting the 64-entry cap, at 81 candidates (F5) | — | — | the last **21%** of the candidate saving |

What this is worth on a real repository is **unmeasured** by me: I ran no
Box2D or cglm repair here (this target is the prototype, and the machine is
shared). The shape that would carry it over — one refused pass re-run — is
`candidates x mean seconds per candidate`, and both factors are measured
elsewhere in this research round, not here.

Two further gains are visible but **unmeasured**: (i) the negatives carry their
`why` (the exact failing test), so a class-level index of "which test kills this
kind of candidate" is available for free from data already collected; (ii)
`rank.py`'s `RETRIED` bit is a *veto* the ranking law already owns, and a
populated negatives store is exactly the observation that would set it — that
would skip whole candidate **classes**, not individual candidates. Neither was
measured here.

## 6. Defects

- **D1 — actuation. `HARVEST_COUNTEREXAMPLE` is actuated as a report, never as
  a memory.** `loop.py:346/407` and `guard.py:719` write it; nothing in `src/`
  reads it (F1). Consequence measured: 18 of 18 candidates re-adjudicated on a
  second run (F2) and 16 of 16 pass-0 rejections re-adjudicated by the
  escalation pass inside a single run (F3). Not a wrong ruling — the law ruled
  `HARVEST_COUNTEREXAMPLE` on byte 64 and the body harvested; it just never
  looks at what it harvested. One lookup before `loop.py:305` closes it.
- **D2 — actuation. The 64-entry cap and the unread `tried_more`.**
  `loop.py:346/407` cap `tried_log` per `repair()` call, and `tried_more`
  (`loop.py:351/412`) is read nowhere, not even by `write_refusal`. Measured
  cost at 81 candidates in one file: 17 rejections (21%) unavailable to any
  read-back (F5).
- **D3 — wording.** `guard.py:105-107` says "each is logged with the test that
  failed it" while `attempts` holds at most 64 per file; at N=81 that sentence
  described 64 of 81 and the report gave no count of the missing 17 (F5).
  Separately, a fully-memoised refusal drops the evidence sentence and the law
  citation entirely (F6) — that one is a defect in the *prototype*, and the fix
  (count skipped negatives into `attempts` / `acts_tried`) is stated in F6.
- **D4 — a correctness risk in the naive form of this proposal, not in
  fluidfix.** A negatives store keyed on `(site, candidate)` alone **loses
  repairs**: measured, run 2 refused a candidate that was green
  (`safety_naive.out`, F4). The brief's framing that this is "a pure speed win
  with no correctness risk" holds only for the tree-scoped form; the unscoped
  form is not safe, and I measured the counterexample rather than assuming it.
- **No wrong ruling found.** Every ruling observed here (`byte 64`,
  `byte 4/5`, `byte 1`) matched the situation as measured.

## 7. Verdict

Keeping rejected candidates as tree-scoped negatives is a measured speed win —
100% of a repeated refusal's candidates (18/18) and 84.2% of the escalation
pass's candidates (16/19, 44→28 pytest invocations, 14.6s→9.3s) removed with the
repair landing byte-identical — and 79% of it needs only a read-back of the
`last_refusal.json` fluidfix already writes; but the negatives must be keyed on a
tree fingerprint, because the unscoped form was measured losing a repair.
