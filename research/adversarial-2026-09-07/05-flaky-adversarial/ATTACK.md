# 05-flaky-adversarial — a flake shape that survives re-confirmation

## 1. Target

Defeat the HIDDEN lane (`loop.py:356-397`, `FLUIDFIX_CONFIRM` default 1) with a suite
that fails on a **schedule** rather than at random, so every confirmation run agrees
with the coarse run and a wrong candidate ships.

## 2. Attack design

`_confirm_runs()` takes `k` extra `oracle.check()` calls **back to back, in the same
second, against the same tree**, and treats agreement as evidence. That is only
evidence under an assumption the code never states: that the runs are *independent
samples*. The 14% → 0% measurement quoted in the source was taken against a flake
that skips its assert with probability ½, where independence holds and `k` extra runs
cut the false-accept rate by `2^-k`.

If leniency is instead a deterministic function of the run counter, the samples are
perfectly correlated: `k+1` consecutive runs inside one lenient window carry exactly
as much information as one. Confirmation then costs the attacker nothing but a
slightly wider window — it does not change the outcome, only the price.

Two schedule families were tried:

* **(F1) periodic** — the strict check runs every Nth invocation.
* **(F2) failure-armed cooldown** — the strict check is suppressed for K runs *after
  it has failed S times*. This is the "flaky-test quarantine" pattern real CI setups
  run (`pytest-rerunfailures`-style auto-xfail, "skip after N strikes so it stops
  blocking the pipeline", a backoff on an expensive golden comparison). Its important
  property is that it **self-phases**: fluidfix's own red baseline probes are what
  arm it, so the lenient window opens exactly when candidate judging begins. The
  attacker does not have to know fluidfix's run schedule; fluidfix supplies the phase.

## 3. Attempts

Environment: `.venv/bin/fluidfix`, every run under `bin/run.sh <seconds> …`
(`nice -n 15` + a perl `alarm` process-group kill — this machine has no coreutils
`timeout`). One run at a time. Nothing outside this directory was written or read
for mutation; fluidfix's source is untouched.

**A0 — recon (no flake).** `fixtures/victim_recon`, strict suite, conftest logs every
pytest invocation (`logs/recon.json`). fluidfix repaired correctly. Learned the run
schedule, which the whole attack is calibrated against:

| # | pytest argv | what it is |
|---|---|---|
| 1 | `-x --tb=long` | `failing_output()` — build the packet |
| 2 | `--lf --cov=…` | localisation coverage |
| 3 | `-p no:cacheprovider --tb=no` | `oracle.green()` precondition |
| 4 | `--lf --cov-fail-under=0` | candidate 1, fast gate |
| 5 | `-p no:cacheprovider --tb=no` | candidate 1, full suite → green |
| 6,7 | `--lf` then full | **the confirmation pair** |

So a *rejected* candidate costs 1 pytest process (fast gate only) and an *accepted*
one costs `2·(CONFIRM+1)` = 4. `fluidfix guard` prepends 3 more baseline runs (6
total) before the same tail.

**A1 — F1, periodic, untuned, DEFAULT confirm.** `fixtures/period/conftest.py`,
`bin/sweep_period.sh`, all 35 phases of PERIOD 2..8. **0/35 landed** — full log in
`logs/psweep_summary.txt`. Every phase was stopped by one of two entry gates:

> `suite is green — nothing to repair (refusing to search)`
> `refused: no failing test — nothing to repair`

A mostly-lenient suite cannot get past runs 1–3, which must *all* be red. This is a
real defence and it kills the naive "every Nth run" flake outright.

**A2 — F2, quarantine, untuned grid, DEFAULT confirm.** `fixtures/quarantine/conftest.py`,
`bin/sweep_quarantine.sh`, STRIKES 1..6 × COOLDOWN 1..6 on victim **A2** (a defect with
**no correct repair in the vocabulary** — fluidfix must refuse it). Result
(`logs/qsweep_summary.txt`): **6/36 shipped a wrong repair**, in one clean contiguous
block — `STRIKES ∈ {3,4}` (= the number of red baseline runs before the first candidate)
× `COOLDOWN ≥ 4` (= `2·(CONFIRM+1)`). Outside that block fluidfix refused. Both
coordinates are ordinary values for a real quarantine plugin.

**A3 — F2 against the unattended `guard` path.** `bin/sweep_guard.sh`, STRIKES 4..8 ×
COOLDOWN 2,4,6 (`logs/gsweep_summary.txt`): **4/15 wrote a wrong repair to disk**, at
`STRIKES ∈ {6,7}` × `COOLDOWN ≥ 4` — 6 being `guard`'s baseline-probe count. The
attack is not specific to `fluidfix repair`.

**A4 — does confirmation help at all?** `bin/sweep_confirm.sh`, `FLUIDFIX_CONFIRM`
0/1/2/3 × COOLDOWN 2/4/6/8 (`logs/sweep_summary.txt`). A perfect staircase:

| | K=2 | K=4 | K=6 | K=8 |
|---|---|---|---|---|
| **CONFIRM=0** | ship | ship | ship | ship |
| **CONFIRM=1 (default)** | refuse | **ship** | ship | ship |
| **CONFIRM=2** | refuse | refuse | **ship** | ship |
| **CONFIRM=3** | refuse | refuse | refuse | **ship** |

`FLUIDFIX_CONFIRM=k` is beaten by `COOLDOWN ≥ 2(k+1)`, exactly. Each extra
confirmation buys two more lenient runs of window and nothing else. There is no `k`
that closes the shape — the ceiling is set by the flake's period, which is the
attacker's (or the CI plugin author's) parameter, not fluidfix's.

**A5 — time-based leniency.** Not reproduced. Every clock-driven variant I designed
either arms on the first failure (and is then killed by the same entry gate as A1) or
reduces to A2 with the window measured in seconds instead of runs. Reported as
untested rather than claimed.

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED (primary)

Reproduce:

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/05-flaky-adversarial
bin/build_victim.sh fixtures/victim_S1 A2
VICTIM_STRIKES=6 VICTIM_COOLDOWN=4 \
  bin/run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard fixtures/victim_S1
diff -u fixtures/victim_S1/money.py.pristine fixtures/victim_S1/money.py
```

fluidfix says (`logs/S1_guard.txt`):

```
[14:39:18] money.py: repaired line 5 in 3 suite runs (1.3s):
  - return a - b
  + return b - a
```

and writes (`logs/S1.diff`):

```diff
 def combined(a, b):
-    return a - b
+    return b - a
```

`test_combined` asserts `combined(3, 4) == 12`. The original returned −1; the shipped
"repair" returns 1. No candidate in the vocabulary can satisfy this test, so the only
correct outcome was a refusal. The discriminating test was **skipped in all four runs
that judged this candidate** (`fixtures/victim_S1/runs.log`, invocations 7–10).

`logs/A2_confirm_default.json` is the same S1 on the `repair` path
(`VICTIM_STRIKES=3 VICTIM_COOLDOWN=4`, default `FLUIDFIX_CONFIRM`).

**Classification: `observation`.**

* Byte passed to the law: `situation(BUILT=True, AMB=False, CAPPED=False)` = `0x201`.
* Act returned: `SHIP`. Correct for that byte — I am not claiming a `ruling`.
* The byte is wrong in one bit. `BUILT` is set at `loop.py:398` from `ok`, and `ok`
  came from a suite that never executed the only assertion that separates the
  candidate from the defect. The candidate was never refuted *or* confirmed; it was
  not measured. On the truthful measurement it never enters `greens`, the law is
  never consulted (`_rule` returns `None` on an empty `greens`), and the code refuses
  — the law's statement for that state being `situation(REFUTED=True)` = `0x240` →
  `HARVEST_COUNTEREXAMPLE`.
* This is the *same* defect class the HIDDEN lane was added to fix, and the source
  comment already names it: "the defect was setting BUILT from a measurement that did
  not hold still." The lane narrowed the class (it removes random flakes) without
  closing it, because a re-check is a **repetition** of the measurement, not an
  independent one.

### S1/S3 — the wrong green shipped over a correct one that was already in hand

```sh
bin/build_victim.sh fixtures/victim_A1 A1
VICTIM_STRIKES=3 VICTIM_COOLDOWN=4 \
  bin/run.sh 300 .../fluidfix repair fixtures/victim_A1 --file money.py --json
```

`logs/A1_repair.json`:

```json
"repaired": true, "new_line": "    return b - a",
"greens": ["    return b - a", "    return a + b"],
"ambiguous": false, "reason": "engine law: BUILT -> SHIP"
```

Here the *correct* repair (`a + b`) was found and recorded as a green, and fluidfix
shipped the flake-manufactured one anyway. Both greens sit at line 5 but in different
candidate sets, and `set_amb` is only raised for two greens **inside one set**
(`loop.py:399-407`), so `AMB` was reported False on a record that lists two passing
programs. The repo is left with a **red suite** and a report that says "repaired":

```
FAILED tests/test_money.py::test_combined - assert 1 == 7
```

Classification: `observation` for the false green (as above), compounded by the known
AMB-proxy surface C for the choice between them. The `"ambiguous": false` next to a
two-element `greens` list is a `wording` defect in its own right.

### S3 — the refusal blames the user whenever confirmation *works*

`logs/sweep_c1_k2.json` (CONFIRM=1, COOLDOWN=2 — the lane fires and holds). The
harvest log is honest:

```
"why": "green on one run, RED on re-check — the suite does not hold still here …
        (engine law: HIDDEN -> CHANGE_GRANULARITY)"
```

but the top-level `reason`, which is what `RepairResult.summary()` prints, is:

> `every candidate left the suite red — fault is outside this vocabulary or the
> observations are wrong`

and `guard` headlines it as (`logs/gsweep_s6_k2.txt`):

> `REFUSED: fault is outside the taught vocabulary … teach it once: docs/TEACHING.md`

with `write_refusal()` writing the same default `hint` (`guard.py:714-716`). fluidfix
**detected a non-deterministic suite** and then told the user to go teach it a fault
class. That is the exact wrong remedy, and it is the message a user sees on every run
where the defence succeeds. The truth is present in `tried_log` /
`rejected_candidates`, so this is a headline defect, not concealment — S3, `wording`.

Minor, same family: the S1 run reports "3 suite runs" while `runs.log` shows 11
pytest processes. `res.suite_runs` counts neither the fast gate nor the confirmation
runs, so a user auditing the number cannot see that confirmation happened at all.

## 5. What defended

* **The three red baseline probes.** `failing_output()` → coverage `--lf` →
  `oracle.green()` must *all* come back red before a single candidate is tried
  (`guard` needs six). This is what took family F1 to 0/35: a flake that is lenient
  most of the time cannot open the search. It is a much stronger defence than the
  confirmation lane, and it is the reason the successful shape had to be
  *failure-armed* rather than periodic.
* **The fast gate.** A rejected candidate costs one pytest process, so a lenient
  window has to be 4 runs wide, not 2, to buy an acceptance. Cheap, and it doubled
  the price of the attack.
* **The HIDDEN lane itself, within its assumption.** COOLDOWN < 2(CONFIRM+1) was
  refused every time, with the accurate `HIDDEN -> CHANGE_GRANULARITY` reason in the
  harvest log. Against an i.i.d. flake it does what the source claims.
* **`_still_reports_failures`** was never bypassed; the flake had to make the suite
  genuinely report `1 skipped`, not fake an exit code.
* The tree was byte-identical to pristine after every refusal (checked in
  `bin/sweep_guard.sh`); no rollback failure, no S2.

## 6. Verdict

fluidfix held against random and periodic flakes, but **not** against a
failure-armed leniency window: a quarantine-style suite that suppresses its failing
test for K runs after S failures ships a wrong repair to disk at default
`FLUIDFIX_CONFIRM=1` whenever S matches the baseline-probe count (3 for `repair`, 6
for `guard`) and K ≥ 2·(CONFIRM+1) — and no value of `FLUIDFIX_CONFIRM` closes it,
because consecutive re-runs of a scheduled flake are one measurement, not many.
