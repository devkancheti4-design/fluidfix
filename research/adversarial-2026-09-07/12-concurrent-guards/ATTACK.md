# 12-concurrent-guards — ATTACK.md

## 1. Target

Two fluidfix guards on one repo at once, and a guard running while a user edits a
file mid-search: does `.fluidfix/inflight.json` or the rollback clobber the other's work?

## 2. Attack design

fluidfix's integrity story is a two-part promise:

* **in-process rollback** — `loop.repair()` reads the target once into `src`
  (`loop.py:245` region), applies every candidate to the *real* file, and writes
  `src` back after each one. `finally: _write(path, src)` (`loop.py:432-438`)
  guarantees a byte-exact restore.
* **crash rollback** — `begin_inflight()` journals the original bytes to
  `.fluidfix/inflight.json` before the first mutation; `recover_inflight()`
  (`guard.py:472-478`, `coracle.py:682`) puts the file back on the next start;
  `end_inflight()` clears it.

Both parts assume **fluidfix is the only writer and the only runner**. Reading
`loop.py:108-146` there is no lock, no PID/owner field on the journal record, no
staleness check, and no re-read of the target. `grep -rn "flock\|LOCK_EX\|O_EXCL"
src/fluidfix/*.py` returns nothing.

So three properties should break:

* **P1** `src` is a snapshot from t=0. Any write by anyone else to that file
  during the search is overwritten by the next rollback. A concurrent *user* edit
  is therefore silently reverted.
* **P2** `recover_inflight()` writes `rec["original"]` over whatever is on disk
  *now*, unconditionally, before the suite is even run. A journal left by a killed
  run outlives the user's own subsequent fix.
* **P3** `end_inflight()` is `os.remove()` on a shared path with no ownership
  check. Guard B deletes guard A's journal, opening a state — *candidate mutation
  on disk, no journal* — that a single run can never enter.

All three are integrity (S2), not ruling. The engine law is never consulted on any
of them.

## 3. Attempts

Harness: `./tmo SECONDS cmd...` (nice -n 15 + a perl `alarm`, kills the process
group; this machine has no coreutils `timeout`). Fixtures in `fixture/`, run
outputs in `out/`, scratch repos in `work/`. One run at a time.

### Attempt 0 — baseline (control)

`./tmo 120 .venv/bin/fluidfix guard work/base` on `fixture/victim` (an
off-by-one `if units > 10:` that should be `>= 10`):

```
[14:31:36] vpkg/calc.py: repaired line 10 in 8 suite runs (13.6s):
  - if units > 10:
  + if units >= 10:
```

Clean repair, 8 suite runs, ~13.6s. That is the window the rest of the attacks use.

### Attempt 1 — user edits the file mid-search — **SUCCEEDED (S2)**

`./attack1_user_edit.sh`. Starts a guard, waits 4s (mid-search, after several
candidate suite runs), then appends a new `tax()` function to `vpkg/calc.py` —
the ordinary act of a developer working in their editor while CI-style
maintenance runs in another terminal.

fluidfix reported a clean repair and **deleted the five lines the user wrote**.
Reproduced 2/2.

### Attempt 2 — two guards, naive — partial

`./attack2_two_guards.sh`. Guard A at t=0, guard B at t+4s. Both ran; A shipped
`if units > 9:`, B printed

```
  recovered vpkg/calc.py: a previous run was killed mid-candidate; original bytes
  restored from the journal
```

and then refused with *"fault is outside the taught vocabulary"*. The final tree
happened to be green, so **not an S2 by itself**, but it establishes two facts the
later attacks weaponise: (a) B really does write A's journalled bytes over the
live file while A is still searching, and (b) B really does delete A's journal.
It also produces two false claims — no run was killed, and the refusal reason is
not the real cause — logged here as S3 but left to agents 16/11 to score.

### Attempt 3 — stale journal vs. the user's own fix — **SUCCEEDED (S2)**

`./attack3_stale_journal.sh`. Realistic sequence, no concurrency needed:

1. Guard A is SIGKILLed mid-candidate (the scenario the journal exists for).
   Journal left behind, file left mutated.
2. **The user fixes the bug by hand**, correctly, and adds a new `tax()`
   function. Their suite is now green (`user's suite rc=0`).
3. The user runs `fluidfix guard` again.

`recover_inflight()` fired *before* `oracle.failing_output()`, overwrote the
user's green file with the stale defective bytes, and fluidfix then "repaired"
the defect it had just re-introduced. Reproduced 2/2.

### Attempt 4 — offset sweep for a refusal-clobbers-a-ship race — FAILED

`./attack4_sweep.sh`, offsets 1/3/5/7/9s, B given `--budget 14`. I was hunting
for B's `finally: _write(path, src)` writing a pre-A snapshot over A's shipped
repair. All five ended green (`out/a4.summary`). B's budget cut it before it had
written enough candidates for `wrote=True` to matter at the right moment. The
race is real in the code but I did not land it; not reported as a finding.

### Attempt 5 — journal theft, then SIGKILL — **SUCCEEDED (S2, strongest)**

`./attack5_journal_theft.sh` → `./attack5b_stranded_red.sh` →
`./attack5c_midsearch_strand.sh` → `./attack5d_red_strand.sh`.

The poll condition is the invariant fluidfix is supposed to hold:
*journal absent **and** file mutated **and** guard A still alive*. In a single
run that is unreachable — `begin_inflight` precedes the first mutation and
`end_inflight` follows the last restore.

5/5b hit the window 8/8 times but always caught A's own green ship, so the tree
stayed green. 5c/5d fixed that with `fixture/victim-red`, whose first candidates
are *red* (`if score > 60:` should be `< 60`; 4 suite runs, 3 of them red) and a
3.0s test sleep to widen each candidate's residency on disk. First trial landed
it.

## 4. Outcome

### F1 — a concurrent user edit is silently deleted by the rollback — **S2**

Repro:
```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/12-concurrent-guards
./attack1_user_edit.sh
diff -u out/a1.useredit.py out/a1.after.py
```

What the user had on disk vs. what fluidfix left (`out/a1.useredit.py` →
`out/a1.after.py`):
```diff
@@ -14,8 +14,3 @@
 
 def bill(units, price):
     return total(units, price) * discount(units)
-
-
-def tax(amount):
-    """USER EDIT: written by the human at t+4s, while the guard was running."""
-    return amount * 0.08
```

fluidfix's report (`out/a1.guard.log`) — no mention of the five lines it removed:
```
[14:32:11] vpkg/calc.py: repaired line 10 in 8 suite runs (13.6s):
  - if units > 10:
  + if units >= 10:
```

**Classification: actuation.**
Observation byte passed: `situation(BUILT=True)` = **513** (`0b1000000001`),
`AMB=False` (one green, one site), `CAPPED=False`.
Act the law returned: **SHIP**.
On the correct byte the law would have ruled *the same* — SHIP is right for a
green, unique repair, and this is not a `ruling` defect. The law's SHIP act means
"write this one-line repair". What the body did instead was write a whole-file
image reconstructed from `raw`, the t=0 line snapshot (`content = "\n".join(new)`,
`loop.py`), which silently reverts every byte of the file the law never looked at.
There is a secondary observation gap behind it: nothing measures that the target
changed under the search, and no bit in `BITS` carries it (`NOTWIN`, `HIDDEN`,
`SELF` are documented as never set), so the law could not have been asked.

### F2 — a stale journal reverts the user's own hand-fix and deletes their new code — **S2**

Repro:
```
./attack3_stale_journal.sh
cat out/a3.state
diff -u out/a3.user_fixed.py out/a3.final.py
```

`out/a3.state` shows the user's suite was **green** (`user's suite rc=0`) before
the guard ran. What fluidfix then did (`out/a3.user_fixed.py` → `out/a3.final.py`):
```diff
@@ -6,7 +6,7 @@
 def discount(units):
-    # FIXED BY THE USER, by hand, after fluidfix died. Reviewed. Correct.
+    # DEFECT: should be `units >= 10`
     if units >= 10:
@@ -14,8 +14,3 @@
 def bill(units, price):
     return total(units, price) * discount(units)
-
-
-def tax(amount):
-    """USER CODE written after the crash. Not fluidfix's to touch."""
-    return amount * 0.08
```

`out/a3.run2.log`:
```
  recovered vpkg/calc.py: a previous run was killed mid-candidate; original bytes restored from the journal
[14:34:35] vpkg/calc.py: repaired line 10 in 8 suite runs (15.3s):
  - if units > 10:
  + if units >= 10:
```

fluidfix took a green repo, made it red, deleted a function, and reported a
routine repair. The one-line notice never says "and I overwrote your file".

**Classification: observation.**
No observation byte was formed at all. `recover_inflight()` is called at
`guard.py:472-473`, *before* `oracle.failing_output()` and before any call to
`decide()`. The record written by `begin_inflight` (`loop.py:113-121`) carries
only `{file, original, started}` — there is no hash of the mutation it left, so
the body cannot measure "does the file on disk still hold what I left?", and no
`started`-age check, so it cannot measure "is this record stale?". Had the bit
"the on-disk file no longer matches the journalled mutation" been measured and
delivered, the honest act is to leave the file alone and tell the user the
journal is stale. Instead an unlawed `open(target,"w")` runs unconditionally.

### F3 — guard B deletes guard A's journal, stranding a wrong mutation with no way back — **S2**

Repro:
```
./attack5d_red_strand.sh
cat out/a5d.trials
diff -u fixture/victim-red/vpkg/calc.py out/a5d-1.stranded.py
ls -la work/a5d-1/.fluidfix
```

`out/a5d.trials`:
```
trial 1: A journalled
  window hit: A ALIVE, journal ABSENT, disk holds:     if score > 59:
trial=1 hit=1 journal=no line10=if score > 59:             suite_rc=1
  *** STRANDED RED MUTATION, NO JOURNAL (trial 1) ***
```

What the repo was left holding — fluidfix's own rejected candidate, not the
user's code:
```diff
 def grade(score):
     # DEFECT: should be `score < 60`
-    if score > 60:
+    if score > 59:
         return "F"
     return "P"
```
```
$ ls -la work/a5d-1/.fluidfix
total 0            <- the journal is GONE
$ pytest -q work/a5d-1
2 failed, 3 passed in 3.02s
```

Neither guard printed anything (`out/a5d-1.A.log` and `.B.log` are both empty).
The user is left with a red suite, a mutation they never wrote, and no record of
their original bytes. This is precisely the Box2D `parallel_for.c` incident the
journal was added to prevent (`loop.py:80-93`) — restored by a second guard.

The window is reachable **only** with two runs. `attack5b` confirms the
single-run invariant holds: 8/8 trials, the journal covered every mutation.

**Classification: observation.**
Again no byte reaches the law: `end_inflight()` (`loop.py:123-128`) is a bare
`os.remove()` on a shared path, called from `recover_inflight` and from
`repair()`'s `finally`. The journal record has no `pid`/`owner`/`boot-id` field,
so "is this journal mine?" and "is its writer still alive?" are bits that cannot
be measured from what is recorded. On a correct byte — journal present, owner
alive, not me — the honest act is to refuse to start (another guard holds this
repo), not to delete the record and race.

## 5. What defended

* **The single-run rollback is genuinely sound.** `attack5b_stranded_red.sh`
  polled at 20ms across 8 trials for "mutation on disk, no journal" and, with one
  guard, never found it; `begin_inflight` strictly precedes the first mutation and
  `end_inflight` strictly follows the last restore. `attack5.sh` needed a *second*
  process to open the hole. Attack 11's single-process SIGKILL attack should find
  this defence holding.
* **The `finally:` block is unconditional.** Every path out of `repair()` —
  refusal, deadline, exception — restores `src`. Attempt 4's five offsets all
  ended with a green tree because of it. The defect is *which* bytes it restores,
  never *whether* it restores.
* **The engine law was never wrong.** Every ship in every attack was
  `situation(BUILT=True)` = 513 → `SHIP`, on a candidate that genuinely passed
  the suite, re-confirmed by the `FLUIDFIX_CONFIRM` HIDDEN lane (default 1). I
  found no `ruling` defect, and I did not try to weaken any law, env var, or
  source file to land these.
* **AMB / CAPPED were not implicated.** These are integrity findings that sit
  entirely below the decision layer.
* **The mutation is always a syntactically valid, compile-checked candidate** —
  F3 leaves a wrong program, not a corrupt file.

## 6. Verdict

fluidfix's rollback is correct against *one* process and *no* concurrent writer,
and it holds absolutely there — but it takes exclusive ownership of the repo
without taking a lock, so it fails as S2 in all three ways this target asks about:
a user's concurrent edit is deleted by the stale-snapshot rollback (F1), a stale
journal silently overwrites the user's own hand-fix and their new code (F2), and a
second guard deletes the first's journal and strands a red mutation with no way
back (F3).

---

### Files

| path | what |
| --- | --- |
| `tmo` | nice+perl-alarm timeout wrapper (no coreutils `timeout` on this host) |
| `fixture/victim/` | off-by-one `>` / `>=`, ~1.2s suite |
| `fixture/victim-slow/` | same, 3.0s suite (wider candidate window) |
| `fixture/victim-red/` | first candidates are RED — used for F3 |
| `attack1_user_edit.sh` | F1 |
| `attack2_two_guards.sh` | attempt 2 (journal theft observed) |
| `attack3_stale_journal.sh` | F2 |
| `attack4_sweep.sh` | attempt 4 (failed race hunt) |
| `attack5_journal_theft.sh`, `attack5b_stranded_red.sh`, `attack5c_midsearch_strand.sh`, `attack5d_red_strand.sh` | F3 |
| `out/` | all logs, before/after files, journal traces |
| `work/` | scratch repos, including the corrupted `work/a5d-1` |

No file outside this directory was written; no git state was changed; no fluidfix
source, law, or `FLUIDFIX_*` default was modified.
