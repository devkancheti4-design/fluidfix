# ATTACK — 11-rollback-kill

## 1. Target
Kill fluidfix with SIGKILL at every phase (mutation, build, suite run, between
candidate sets) and prove the victim repo is NOT byte-identical afterwards.
Attack the crash-journal window (`.fluidfix/inflight.json`).

## 2. Attack design
fluidfix's crash-safety promise (loop.py:79-93): before the first mutation the
original bytes are journalled to `.fluidfix/inflight.json`; "a later run — or the
same one restarting — puts the file back." I attacked three properties of that
design:

- **The write is not atomic.** `_write` (loop.py:74-76) is
  `open(path,"w"); f.write(content)` — truncate *then* write. A SIGKILL between
  the truncate and the flush leaves a torn/zero-byte file on disk.
- **The journal is a single slot, overwritten with no guard.** `begin_inflight`
  (loop.py:113) blindly records *whatever is on disk now* as `original`; the
  `finally` (loop.py:432-438) restores the tree to that same on-disk `src` and
  then `end_inflight` deletes the journal.
- **Recovery is only wired into two of the four entry points.**
  `recover_inflight` is called on startup by `guard` (guard.py:473) and `cguard`
  (coracle.py:683) — but NOT by `fluidfix repair` (cli.py:57-83, calls
  `repair()` at :77 with no recover) nor by `fluidfix jguard`
  (javaoracle.py:189-223, calls `repair()` at :212 with no recover).

Hypothesis: a kill under `repair`, followed by the *natural* retry (`repair`
again), makes fluidfix journal its own leftover mutation as the "original,"
destroying the true recovery point — so the repo is left in a broken state the
user never had, and even the sanctioned recovery restores that broken state.

Victim: a minimal repairable Python repo (`victim_template/`) — the
`count_above` `x >= t` bug from the project's own `tests/test_e2e.py`, with a
`time.sleep(VICTIM_SLEEP)` in the test to widen the "candidate applied on disk"
window. Every fluidfix run goes through `runlim.sh` (nice -n 15 + a perl-alarm
hard cap; no coreutils `timeout` on this box) in a fresh session, and I SIGKILL
only that session's own process group.

## 3. Attempts (including failures / defences that held)

**Attempt 0 — harness self-check (my own bug, fixed).** My first `runlim.sh`
used perl `setpgid` to put the child in its own process group; my launcher's
`killpg` then hit only perl, and fluidfix ran to completion. Caught it because
the "killed" victim kept progressing to the finished fix. Fixed the wrapper so
fluidfix shares the session group, and added `verify_dead_and_stable` (asserts
the process is gone AND the file stops changing) to every kill. All results
below are post-fix and verified clean (no lingering processes).

**Attempt 1 — single kill mid-candidate under `repair` (exp1_single_kill.py).**
Killed the instant a candidate hit disk. Left on disk: `mod.py` = `n = -1` (a
broken candidate, neither pristine nor a correct fix) + a new `.fluidfix/`
dir + `inflight.json`. `journal.original == pristine`: True. So immediately
after the kill the working tree is corrupt; recovery is DEFERRED to a future
`guard`/`cguard`. Manifest diff vs pristine: `CONTENT mod.py`, `ADDED
.fluidfix/inflight.json`, `DIR+ .fluidfix`. NOT byte-identical.

**Attempt 2 — the two recovery paths (exp2_recovery_paths.py).**
- PATH A (defence): `recover_inflight()` — exactly what `guard`/`cguard` run on
  startup — restored `mod.py` byte-exact to pristine and removed the journal.
  **This defence held.**
- PATH B (attack): the natural `fluidfix repair` retry does NOT recover. It read
  the leftover `n = -1` as the user's source, and on refusing, its own
  byte-exact `finally` restore put the file back to `n = -1` and deleted the
  journal. Final: `mod.py` = broken leftover, journal gone, **pristine original
  unrecoverable from anything fluidfix wrote.**

**Attempt 3 — journal poisoning, double fault (exp3_journal_poison.py).**
Kill #1 under fresh `repair` → leftover L1, `journal.original == pristine`.
Natural `repair` retry, Kill #2 mid-candidate → `journal.original == L1`, NOT
pristine. Then the user runs the *sanctioned* recovery (`recover_inflight`,
i.e. what `guard`/`cguard` do): it restored `mod.py` to L1 (`n = -1`, broken),
NOT pristine. The crash-recovery tool itself handed back a broken variant the
user never had.

**Attempt 4 — torn write, the literal "during mutation" phase
(exp4_torn_write.py).** Padded the source to 1.54 MB and polled for a truncated
size during `_write`. Caught on the first try: `mod.py` left at **0 bytes** after
SIGKILL. Confirms `_write` is non-atomic. (Journal still held pristine, so
`guard` could recover — but a `repair` retry would journal the empty file as
"original" and destroy it, per Attempts 2/3.)

**Attempt 5 — file mode across kill+recover (defence check).** chmod 0755 the
source; after kill and `recover_inflight`, mode stayed 0755 and content matched
pristine. The recovery MECHANISM preserves content (read/written with
`newline=""`, byte-exact) and mode (`open("w")` truncates in place). **This
defence held** — the bug is not in `recover_inflight` itself, it is which entry
points call it and the ungated single-slot journal.

## 4. Outcome

**S2 — CORRUPTION (repo left in a state the user never had; recovery point
destroyed). Reproduced.**

Reproduction (each ~seconds, one at a time):
```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/11-rollback-kill
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
nice -n 15 $PY exp1_single_kill.py      # single kill: mutation + journal left on disk
nice -n 15 $PY exp2_recovery_paths.py   # guard recovers (defence) vs repair-retry destroys
nice -n 15 $PY exp3_journal_poison.py   # double fault: sanctioned recovery -> broken variant
nice -n 15 $PY exp4_torn_write.py       # SIGKILL during _write leaves a 0-byte file
```

The "diff fluidfix wrote" — the state a user is left with after a kill under
`repair` + the natural `repair` retry (exp2/exp3):
```
 def count_above(xs, t):
-    n = 0
+    n = -1
     for x in xs:
         if x >= t:
             n += 1
     return n
```
plus `.fluidfix/inflight.json` deleted (recovery point gone) and a residual
`.fluidfix/` directory. The suite is RED; the file is a variant the user never
wrote and can no longer recover through fluidfix.

**Classification: actuation** (integrity defect, not a law ruling). The engine
law (`decide`/`situation`) is never consulted on this path — `cmd_repair`,
`jguard_once`, `begin_inflight`, `end_inflight` and `recover_inflight` are pure
plumbing. There is therefore **no observation byte and no law act** to print:
per the brief's own note this is not a `ruling`. The violated invariant is
structural — "restore the tree before mutating, and never journal a live
mutation as the original." The law would have nothing to fix here; the body
does the wrong thing regardless of any byte. Specifically:
- the actuator that should restore the tree (loop.py:433-434 `_write(path, src)`)
  restores to `src`, which on a non-recovering entry point IS the prior run's
  leftover mutation; and
- `begin_inflight` (loop.py:245) overwrites the only recovery slot with that
  leftover before anyone restored from it.

**S3 corollary (false-confidence enabler):** the design comment at
loop.py:436-437 asserts the post-run file is "either its original bytes or an
ACCEPTED repair — both intentional." Under a non-recovering entry point the
file can be a *rejected* candidate's bytes, which is neither.

## 5. What defended
- `guard` (guard.py:472-473) and `cguard` (coracle.py:682-683) DO call
  `recover_inflight` on startup; on a repo whose journal has NOT been poisoned,
  it restores the file byte-exact (exp2 PATH A).
- `recover_inflight` preserves **content** (byte-exact via `newline=""`) and
  **file mode** (`open("w")` keeps the inode/mode) — verified with a 0755 file
  (exp5). The recovery mechanism itself is sound.
- The journal captures pristine bytes *before* the first mutation
  (loop.py:245 precedes every `_write`), so a *single* kill under `guard`/
  `cguard` is fully recoverable — the defect needs a non-recovering entry point
  (`repair`/`jguard`) to bite.

## 6. Verdict
fluidfix did NOT hold on integrity: a SIGKILL mid-candidate under `fluidfix
repair` (or `jguard`) plus the natural retry poisons and deletes the
`.fluidfix/inflight.json` recovery slot, leaving the repo a broken variant the
user never had — S2 corruption, classification **actuation**, because `repair`
and `jguard` never call `recover_inflight` and `begin_inflight` re-journals the
leftover as the original. `guard`/`cguard` recovery and mode/content fidelity
held.
