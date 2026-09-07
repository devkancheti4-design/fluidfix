# 10-rank-veto-abuse — attacking the ranking law's RETRIED veto and class order

## 1. Target

The ranking law's `RETRIED` veto (`rank.py` bit 7) and the priority classes it
orders: build a defect whose true class is ranked so late the budget dies before
reaching it, and where the re-tries the dead veto permits are the difference
between repair and refusal.

## 2. Attack design

`rank.py:24` states the contract: *"RETRIED is a VETO, not a weak signal: a line
already tried and rejected this pass goes last whatever else is true of it.
Without that, a retried line sitting in the traceback frame is re-examined first
every pass."* `guard.py:413` reads a `retried` set into the byte, and
`rank_observations` accepts `retried=` (`guard.py:342`) — but **neither call site
passes it** (`guard.py:511` in the first pass, `guard.py:585` in the escalation
pass). The lane is dead, so the law is handed `RETRIED=0` for every line,
including lines the same guard pass has already exhausted.

That matters because `guard_once` runs the file **twice** when pass 0's packet is
truncated: pass 0 under `t0 + budget/3`, then the escalation pass (engine law
`CAPPED -> RAISE_BUDGET`) rebuilds the packet at full sight and calls
`loop.repair()` **with a fresh `tried` set** (`loop.py:185`). Nothing carries
across. So the escalation re-ranks the identical observation list in the
identical order and re-runs the identical candidates.

The attack therefore needs three properties, all of which are ordinary repo
shapes rather than fluidfix-specific tricks:

1. **A truncated pass-0 packet**, so the escalation stage runs at all. Achieved
   with signal-free covered lines that `localize.py:164-172`'s filter drops.
2. **Decoy lines that outrank the defect.** `NAMED` is the token overlap between
   a line's enclosing `def` and the *failing test's name*. A helper whose name
   echoes the failing test outranks the actual faulty function whenever the fault
   lives one call deeper, in a differently-named function. That is the common
   case, not a contrived one.
3. **A defect that is genuinely in the shipped vocabulary**, so a refusal cannot
   be excused as "out of vocabulary".

### The fixture (`make_victim.py`, 90 decoys, ~280 lines)

    pkg/core.py
      alpha_beta_helper(seed)   90 x `acc.append(a + b)`  (decoys)
                                interleaved with signal-free filler lines
      gamma_delta(x, y)         `return x - y`            (THE DEFECT, wants +)

    tests/test_ledger.py
      test_alpha_beta      FAILS; calls the helper (so it is covered) then
                           asserts gamma_delta(7, 5) == 12
      test_helper_values   PASSES; pins every decoy line

`test_alpha_beta` -> name tokens `{alpha, beta}`. They overlap
`alpha_beta_helper` and not `gamma_delta`. That single fact inverts the order.

### The bytes the law is actually given (`bytes_probe.py`, read-only tap on `rank.rank`)

    AS SHIPPED (guard.py never passes retried=)
      decoy   pkg/core.py:9   byte=0b01101100 (108) NAMED|SIGNALED|CHEAP|DENSE
                              -> law returns priority 2; examined   2 of 110
      DEFECT  pkg/core.py:284 byte=0b00101000  (40) SIGNALED|CHEAP
                              -> law returns priority 3; examined 110 of 110

    WITH THE VETO FED (rank.py's documented contract)
      decoy   pkg/core.py:9   byte=0b11101100 (236) NAMED|SIGNALED|CHEAP|DENSE|RETRIED
                              -> law returns priority 7; examined   3 of 110
      DEFECT  pkg/core.py:284 byte=0b00101000  (40) SIGNALED|CHEAP
                              -> law returns priority 3; examined   1 of 110

The law is correct on both bytes. It is the byte that is wrong.

## 3. Attempts

1. **Control — is the defect repairable at all?** `fluidfix guard --dry-run`, no
   budget: **repaired** `pkg/core.py:284`, `return x - y` -> `return x + y`,
   **93 suite runs, 22.2 s**, byte-exact. So the suite genuinely pins it and the
   class is shipped (`fluidfix kinds` -> `3  flipped-additive  (shipped)`).
   ✔ this is the baseline the refusals below have to be judged against.

2. **`fluidfix guard --budget 60`.** REFUSED after **40.9 s** — 1.84x the clock
   the complete search needs. **Successful attack, see §4.**

3. **`fluidfix guard --budget 45`.** REFUSED after **31.0 s** — 1.4x the needed
   clock. Same shape. **Successful attack.**

4. **Quantifying the waste from the refusal journal.** In both runs the
   escalation pass logged 64 rejections whose `(line, candidate)` sequence is a
   *prefix-identical repeat* of pass 0's 64 — `new = 0`. Line 284 was never
   reached in either pass. (`tried_log` caps at 64 per `repair()` call, so 64 is
   a floor on the duplication, not a ceiling.)
   An earlier run at `--budget 60` on a differently-warmed cache gave
   pass0 = 61 logged, escalation = 64 logged, of which **61 (95 %) were exact
   re-runs and only 3 candidates were new work** — 18 s of escalation clock
   bought three suite runs of progress.

5. **Escalate the same defect to S1 (ship something wrong).** Attempt: let the
   wasted re-tries push the *only* green past the deadline so a lone unproven
   green gets shipped as `BUILT -> SHIP`. **Failed — the defence held.** In
   `guard_sim.py 60 shipped` the escalation did find the green and refused it:
   *"a candidate passes, but the search was cut short before it could be shown
   unique — shipping it would be a guess. Raise the budget and re-run (engine
   law: BUILT+CAPPED -> RAISE_BUDGET)"*. Correct ruling, correct act.

6. **"A class whose retry marking suppresses the real answer."** Could not be
   built, and the reason is itself the finding: **no line is ever marked
   RETRIED**, so retry marking can suppress nothing. The half of the target that
   assumes the veto fires is unreachable in the shipped code.

7. **S2 (corruption).** After every refused run,
   `diff -r --exclude=.fluidfix --exclude=__pycache__ --exclude=.pytest_cache`
   against a freshly generated pristine tree: **identical**. No mutation
   survived, no journal residue mattered. Defence held.

8. **End-to-end counterfactual** (`guard_sim.py`, replays `guard_once`'s exact
   budget arithmetic using fluidfix's own `build_packet` / `rank_observations` /
   `repair`, one delta: the escalation rank call gets `retried=` populated from
   pass 0's own rejection log). Feeding the veto moves the defect from
   *"never examined"* to *"examined first"* (`counterfactual.py`, 18 s share:
   shipped arm = `wall-clock deadline reached mid-search`, no green ever found;
   veto arm = `a candidate passes ... BUILT+CAPPED`, i.e. the repair was found).
   Honest limit: because `repair()` must sweep the whole observation list to
   discharge AMB, and escalation is capped at half the remaining clock, feeding
   the veto turns *"I never looked"* into *"I found it, raise the budget"* — it
   does not turn this fixture's refusal into a SHIP at the same budget. Reported
   as measured, not as hoped.

## 4. Outcome

### S4 — DENIAL. A defect in the shipped vocabulary, refused with 1.84x the needed clock

Reproduction (from this directory; `tmo` is the local nice+alarm wrapper):

    F=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin
    D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/10-rank-veto-abuse
    $D/tmo 60 $F/python $D/make_victim.py $D/runs/cli_b60 90
    cd $D/runs/cli_b60
    $D/tmo 300 $F/fluidfix guard $D/runs/cli_b60 --python $F/python --budget 60

Result:

    REFUSED: fault is outside the taught vocabulary (candidate files tried:
    pkg/core.py). teach it once: docs/TEACHING.md (or run: fluidfix kinds)
    128 candidate(s) were tried and rejected
    real 40.94

versus the same tool on the same tree with no `--budget`:

    pkg/core.py: repaired line 284 in 93 suite runs (22.2s):
      - return x - y
      + return x + y

**Diff fluidfix wrote:** none — the refused runs leave the tree byte-identical.
The diff it *should* have written, and does write when unbudgeted, is:

    --- a/pkg/core.py
    +++ b/pkg/core.py
    @@ -281,4 +281,4 @@
     def gamma_delta(x, y):
         """The real defect lives on the next line."""
    -    return x - y
    +    return x + y

**Classification: `observation`.**
- Observation byte passed, for `pkg/core.py:9` on the escalation pass *after the
  same pass had already tried and rejected it*: `0b01101100` (108) =
  `NAMED|SIGNALED|CHEAP|DENSE`, `RETRIED=0`.
- Act the law returned: **priority 2** — examined 2nd of 110, ahead of the defect.
- What the law WOULD have ruled on the correct byte: `0b11101100` (236), the same
  evidence plus `RETRIED` — **priority 7**, the veto floor, examined behind the
  defect. Measured, not asserted: see `bytes_probe.py` output in §2.
- The defect line's own byte, `0b00101000` (40) -> priority 3, is correct. The
  law is not wrong anywhere here. `guard.py:511` and `guard.py:585` simply never
  measure or deliver bit 7, so 64 of 64 logged escalation candidates were work
  the pass had already done and journalled.

### S3 — FALSE CONFIDENCE. The refusal blames the vocabulary; the clock is what ran out

The report says *"fault is outside the taught vocabulary … teach it once"* about
`return x - y`, which is kind 3 `flipped-additive`, **shipped**, and which the
same binary repairs in 22.2 s. It never mentions `--budget`.

`GuardReport.summary()` (`guard.py:57-99`) has exactly the right branch for this
— its comment says *"Blaming the vocabulary sends the user to write a rule they
already have"* — but it gates on `exhausted = "budget exhausted" in self.hint`.
That hint is only set when the deadline is noticed at the **top of the
`for rel in all_files` loop** (`guard.py:565`). Here the single candidate file
passes that check, the deadline expires **inside** `repair()`, which returns
`reason = "wall-clock deadline reached mid-search — remaining observations
untried"`, the loop then ends normally, and the `any_acts` branch stamps
`REFUTED -> HARVEST_COUNTEREXAMPLE` instead.

**Classification: `observation`** (surfacing as `wording`). The bit "the search
was cut short by the clock" *was* measured — it is sitting in
`result.reason`/`result.greens` — and is never delivered into the byte
`summary()` reads. No law was consulted on this path at all; the branch is
straight code. On the correctly measured situation the existing `elif exhausted`
branch already produces the right text (*"ran out of budget before the fault was
found — this is a SEARCH limit, not a gap in the taught vocabulary"*).

## 5. What defended

- **`BUILT+CAPPED -> RAISE_BUDGET`.** The one path to S1 here was a lone green
  found late and shipped unproven. Every time the search found the green and the
  clock then expired, the engine law refused it verbatim: *"a candidate passes,
  but the search was cut short before it could be shown unique — shipping it
  would be a guess."* This is the single mechanism that kept the whole target at
  S4/S3 instead of S1.
- **Byte-exact rollback + `.fluidfix/inflight.json`.** Two full refused runs,
  128 applied-and-reverted candidates each, and both trees came back
  byte-identical to a freshly generated pristine copy. No S2.
- **The AMB sweep.** `repair()` refusing to stop at the first green is what makes
  the wasted re-tries expensive — but it is also what makes a shipped repair
  trustworthy. It should not be traded away to fix this finding.
- **`--lf` fast gate.** Every decoy was rejected in one cheap suite run rather
  than a full sweep; without it the same fixture would have refused at a far
  larger budget still.
- **The ranking law itself.** All 256 situations behave as documented; the veto
  dominates every other lane exactly as `rank.py` claims. Nothing here is a
  `ruling`.

## 6. Verdict

**fluidfix held against corruption and against shipping a wrong repair, but not
against denial: the `RETRIED` veto its own ranking law calls a veto is never
measured at either call site (`guard.py:511`, `guard.py:585`), so the escalation
pass re-ran 64 of 64 logged candidates it had already rejected, refused a
shipped-vocabulary defect after 1.84x the clock a complete search needs, and
told the user to teach a class that already exists.**

---

### Files kept for re-running

    tmo                 nice -n 15 + perl-alarm timeout wrapper (no coreutils timeout here)
    make_victim.py      builds the fixture; arg 2 = decoy count (90 used)
    probe_rank.py       packet truncation + examined-position, with/without retried=
    bytes_probe.py      the exact observation byte, via a read-only tap on rank.rank
    counterfactual.py   escalation stage only, both arms, from a real refusal journal
    guard_sim.py        guard_once's full budget arithmetic, both arms
    runs/               victim trees and .fluidfix/last_refusal.json for each run

No fluidfix source was modified, no law monkeypatched, no `FLUIDFIX_*` variable
set, and no git state changed. `bytes_probe.py`'s tap around `rank.rank` records
the argument and returns the law's own answer unchanged.
