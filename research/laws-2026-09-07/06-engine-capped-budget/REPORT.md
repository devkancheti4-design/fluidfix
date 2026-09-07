# 06-engine-capped-budget — REPORT

## 1. Target

Sweep `--budget` (150..900) on the fixture of `tests/test_span_edits.py::test_budget_hands_first_pass_over_to_escalation`; confirm BUILT+CAPPED -> RAISE_BUDGET and its message; find the threshold; decide whether the first-pass/escalation split is a code decision.

## 2. Method

Everything I wrote is in `/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/06-engine-capped-budget/`. Nothing under `src/`, `tests/`, `docs/` was touched; no git state changed. macOS has no coreutils `timeout`, so `timeout.py` (kills the process group after N s, exit 124) stands in for `timeout 300`. Every run is `nice -n 15 <venv python> timeout.py 300 <venv python> <script>`, executed strictly one at a time by `run_queue.sh` / `run_queue2.sh` / `run_queue3.sh` (`queue.log`, `queue2.log`, `queue3.log` carry the start/end stamps). The machine is shared with 49 other agents; load average was 2.86 / 3.01 / 3.13 at the start of the three queues, so every wall-clock number below is from a loaded machine and the run-to-run spread is real (see F7).

Read (absolute root `/Users/kanchetidevieswar/neo/fluidfix/`): `src/fluidfix/engine.py`; `src/fluidfix/loop.py` (`_rule` 193-243; its deadline call sites 272, 291; 424); `src/fluidfix/guard.py` (`guard_once` 442-621: docstring 452-459, `first_deadline` 468, `capped0` 485/508/538, the gate 539, escalation 540-616, the `file_share` cap 591-592, `GuardReport.summary` 57-101, `rank_observations` 340); `src/fluidfix/localize.py` (`Packet.truncated` 41, filter/stride 160-175); `src/fluidfix/oracle.py:185-248` (`check`, `failing_output`); `src/fluidfix/cli.py` (60-83 single-file `repair`, 649-653 `--budget` help); `src/fluidfix/coracle.py:755-771`; `src/fluidfix/javaoracle.py:212-221`; `tests/test_span_edits.py:172-226`; `tests/test_engine_fusion.py:71-80`; `CHANGELOG.md` (0.14.0 lines 40-53, 0.7.1); `docs/SCALE.md:125-150`; read-only `git log -S`.

Scripts (rerunnable, next to this report):

- `static_analysis.py` -> `static_analysis.out`: the law's ruling on every byte the body can pack at `loop.py:217` and `guard.py:539`; all 256 inputs split by the CAPPED bit; the fixture's search-space arithmetic.
- `sweep_budget.py <B> <dir>` -> `sweep_<B>.out`, `fixture_<B>/rulings.json`: rebuilds the fixture verbatim (same 800 filler lines, same pad search as the test), wraps `engine.decide`/`loop.decide` to log every ruling with its call site, counts every `Oracle.check`, runs `guard_once(oracle, MechanicalObserver(), budget=B)`. Run at B = 150, 300, 325, 350, 400, 450, 600, 750, 900 — nine points, one at a time.
- `cut_untruncated.py <dir> <B|none>` -> `cut_b30.out`, `cut_none.out`: the same bug in a 76-line file whose first-pass packet is NOT truncated.
- `msg_demo.py <dir>` -> `msg_demo.out`: calls `loop.repair()` directly with a deadline that lands after a green but before the observations are exhausted (part A), the same fixture through `guard_once(budget=18)` (part B), and a static enumeration of which `Result` field every caller reads (part C).
- `tabulate.py` -> `sweep_table.md`; `threshold.py` -> `threshold.out`: pure arithmetic over `fixture_*/rulings.json`, no suite runs.
- `run_queue*.sh`: the exact sequences run.

## 3. Findings

### F1. The law: BUILT+CAPPED -> RAISE_BUDGET confirmed; CAPPED yields to AMB, UNREAD, NOTWIN and HIDDEN

Command: `nice -n 15 .venv/bin/python timeout.py 300 .venv/bin/python static_analysis.py ./fixture_static` (output `static_analysis.out`).

```
loop.py:217  decide(situation(BUILT=True, AMB=..., CAPPED=...)):
  BUILT=1 AMB=0 CAPPED=0  byte=0x01 -> SHIP
  BUILT=1 AMB=0 CAPPED=1  byte=0x21 -> RAISE_BUDGET
  BUILT=1 AMB=1 CAPPED=0  byte=0x03 -> ADD_STATE
  BUILT=1 AMB=1 CAPPED=1  byte=0x23 -> ADD_STATE
guard.py:539 decide(situation(CAPPED=capped0, REFUTED=acts0)):
  CAPPED=0 REFUTED=0  byte=0x00 -> SHIP
  CAPPED=0 REFUTED=1  byte=0x40 -> HARVEST_COUNTEREXAMPLE
  CAPPED=1 REFUTED=0  byte=0x20 -> RAISE_BUDGET
  CAPPED=1 REFUTED=1  byte=0x60 -> RAISE_BUDGET
== all 256 inputs, split by the CAPPED bit ==
  CAPPED=1 (128 inputs): {'RAISE_BUDGET': 16, 'ADD_STATE': 56, 'ADD_MATERIAL': 32, 'AUTHOR_SUCCESSOR': 8, 'RESHAPE': 8, 'CHANGE_GRANULARITY': 8}
```

The 16 CAPPED inputs ruled RAISE_BUDGET are the 8 "clean" ones (CAPPED with any of BUILT/REFUTED/SELF: 0x20 0x21 0x60 0x61 0xa0 0xa1 0xe0 0xe1) plus 8 of the shape BUILT+AMB+UNREAD+CAPPED(+HIDDEN)(+REFUTED)(+SELF) (0x27 0x37 0x67 0x77 0xa7 0xb7 0xe7 0xf7). So BUILT+AMB+CAPPED -> ADD_STATE and BUILT+UNREAD+CAPPED -> ADD_MATERIAL, but BUILT+AMB+UNREAD+CAPPED -> RAISE_BUDGET. Those 8 are unreachable today: the body packs UNREAD only alone (`guard.py:491`). Precedence in general is target 07's; I record only what my sweep touches.

Note also that `CAPPED=0, REFUTED=0` at the gate rules SHIP — the byte 0x00 means "nothing happened". The gate at `guard.py:539` compares `== "RAISE_BUDGET"`, so SHIP there simply skips escalation; nothing is shipped (a green in the first pass returns at `guard.py:521`).

### F2. Fixture arithmetic: the "grind" is 110 + 802 suite runs, and the ranking law puts the bug line at position 400 of 802

Same command, section 2 of `static_analysis.out`:

```
== 2. fixture arithmetic (pad=0, bug at mod.py:403, file has 806 lines) ==
  first pass  (build_packet default max_lines=110): packet lines=110 truncated=True bug_in_packet=False
    observations=110 kinds histogram={12: 109, 1: 1} distinct candidates (= max suite runs, before dedup)=110
  escalation  (max_lines=990, guard.py:578): packet lines=803 truncated=False bug_in_packet=True
    observations=802 kinds histogram={12: 800, 0: 1, 10: 1, 1: 1} distinct candidates=803
    ranking-law position of the bug line among observations: 400 (0 = tried first)
    bug line kinds=[0, 10]; candidates before it: 400
  one suite run (oracle.check, fail-fast --lf path) on this fixture:
    run 1: ok=False 0.33s / run 2: 0.21s / run 3: 0.20s
```

Three consequences. (a) The first pass costs a fixed 110 suite runs (measured 23.4-33.3 s across all nine sweep runs). (b) Since 0.14.0 the search does not stop at the first green, so escalation ALWAYS costs the full 802 candidates (+2 confirm runs) whatever the ranking does; the ranking's position 400 only decides whether a green exists when a deadline lands. (c) The filler lines are observations at all only because kind 12 (`flipped-boolean`, added in 0.8.0, commit c35ca67) matches `True`; `tests/test_engine_fusion.py:74-76` still says the fillers "yield NO observer kinds ... keeping the suite-run count small" — a stale comment, and the 802-run grind the budget test depends on is an accident of that later kind.

### F3. The budget sweep, 150..900 (nine points, all measured)

Commands: `run_queue.sh` (450, 150), `run_queue2.sh` (300, 400, 350, 600), `run_queue3.sh` (900, 325, 750) — each entry `nice -n 15 .venv/bin/python timeout.py 300 .venv/bin/python sweep_budget.py <B> ./fixture_<B>`. Table regenerated by `tabulate.py` into `sweep_table.md`:

| budget | status | elapsed_s | first_pass_end_s | first_pass_runs | suite_runs | greens | final ruling |
|---|---|---|---|---|---|---|---|
| 150 | refused | 92.2 | 33.3 | 110 | 290 | 0 | REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE @ guard.py:612 |
| 300 | refused | 162.0 | 23.4 | 110 | 815 | 2 | REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE @ guard.py:612 |
| 325 | refused | 175.2 | 24.9 | 110 | 688 | 2 | REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE @ guard.py:612 |
| 350 | repaired | 181.5 | 24.1 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |
| 400 | repaired | 185.4 | 24.1 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |
| 450 | repaired | 209.9 | 27.4 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |
| 600 | repaired | 179.8 | 23.4 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |
| 750 | repaired | 239.1 | 32.5 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |
| 900 | repaired | 188.2 | 24.3 | 110 | 914 | 2 | BUILT (0x01) -> SHIP @ loop.py:217 |

**The threshold on this machine sits between 325 and 350 s** (325 refused, 350 repaired). Above it every run repairs, and every repair takes the same 914 suite runs and reaches SHIP through escalation — `result.reason` on all six repaired runs is `'engine law: BUILT -> SHIP (engine law: CAPPED -> RAISE_BUDGET, depth-first)'`, and that `", depth-first"` suffix is appended only in the escalation branch (`guard.py:601`), so the handover the test exists to exercise happens at every budget >= 350, including 600 and 900.

The gate ruled `CAPPED+REFUTED (0x60) -> RAISE_BUDGET` at `guard.py:539` in ALL nine runs (the first-pass packet is always truncated), so escalation was entered every time. At 150 the escalation clock cut the search before any green (`greens=0`, 290 runs of 914). At 300 and 325 escalation found the two confirming greens and was then cut, which is the BUILT+CAPPED lane — `sweep_325.out`:

```
  RULING t=   24.9s          CAPPED+REFUTED (0x60) -> RAISE_BUDGET           at guard.py:539  [suite runs so far: 110]
  GREEN  t=  125.3s  suite run #511 passed
  GREEN  t=  126.1s  suite run #512 passed
  RULING t=  175.2s            BUILT+CAPPED (0x21) -> RAISE_BUDGET           at loop.py:217  [suite runs so far: 688]
  RULING t=  175.2s                 REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE at guard.py:612  [suite runs so far: 688]
RESULT: budget=325 status=refused elapsed=175.2s suite_runs(check)=688 greens=2
  summary='REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py). ...'
```

The law ruled RAISE_BUDGET on a byte that was correctly measured, and the user was told the fault is outside the vocabulary. That is F5.

### F7. The binding constant at the threshold is NOT `--budget`, it is the `file_share` half-cap at guard.py:591-592

`--budget` is documented as "wall-clock cap for the WHOLE guard pass" (`cli.py:649-653`), but no run in the sweep was ever cut by `total_deadline`. Every cut came from the depth-first starvation guard:

```python
# guard.py:589-593
file_share = ((deadline - time.time()) / 2
              if total_deadline is not None else escalate_budget / 2)
result = repair(oracle, rel, observations, candidate_timeout=candidate_timeout,
                deadline=min(deadline, time.time() + file_share))
```

So the ONE file that holds the bug gets `t1 + (budget - t1)/2`, not `budget`. Command: `nice -n 15 .venv/bin/python threshold.py` (output `threshold.out`), pure arithmetic over the recorded `rulings.json`:

```
| budget | status | first_pass_end_s | end_s | cut predicted by total_deadline | cut predicted by file_share/2 |
| 150 | refused | 33.3 |  92.2 | 150.0 |  91.7 |
| 300 | refused | 23.4 | 162.0 | 300.0 | 161.7 |
| 325 | refused | 24.9 | 175.2 | 325.0 | 175.0 |
| 350 | repaired| 24.1 | 181.5 | 350.0 | 187.0 |
| 400 | repaired| 24.1 | 185.4 | 400.0 | 212.0 |
| 900 | repaired| 24.3 | 188.2 | 900.0 | 462.2 |

escalation work W = end - first_pass_end, on the runs that finished it:
  W range on this loaded machine: 156.4s .. 206.6s (same 804 suite runs every time)
file_share/2 binds when  W > (budget - t1)/2, i.e. budget < t1 + 2W.
  t1 (first pass, 110 runs) measured range: 23.4s .. 33.3s
  => threshold budget = t1 + 2W  in  [336s .. 446s]
  total_deadline alone would put the threshold at t1 + W = [180s .. 240s]
```

Every refused run ended within 0.5 s of the `file_share/2` prediction (92.2 vs 91.7; 162.0 vs 161.7; 175.2 vs 175.0) and nowhere near `total_deadline`. Every repaired run finished before its `file_share/2` prediction. The observed 325/350 bracket sits inside the predicted `[336..446]` band. **A user must therefore supply roughly twice the clock the search actually needs** — 350 s of `--budget` to buy ~157 s of escalation work — and no message anywhere says so. The half-cap is correct in intent (a wrong rank-1 file must not starve the others, adversarial review 2026-08-31) but it is applied unconditionally, including when `all_files` has exactly one entry and there is nothing to starve. This fixture has one candidate file (`mod.py`).

### F4. A first-pass DEADLINE cut is not measured as CAPPED (observation defect, masked on the target fixture)

`guard.py:508` and `:538` set `capped0` from `packet.truncated` and from "more candidate files than tried" only. When `repair()` returns because `first_deadline` passed (`loop.py:272/291`), nothing reads that. On the target fixture the packet is truncated anyway, so CAPPED is true for another reason and the gap is invisible. `cut_untruncated.py` removes the mask: same bug, 76-line file, untruncated packet (73 lines), 73 candidates, bug ranked last.

Command: `nice -n 15 .venv/bin/python timeout.py 300 .venv/bin/python cut_untruncated.py ./fixture_cut_b30 30` (`cut_b30.out`):

```
FIXTURE: 76 lines, bug at mod.py:73, first-pass packet lines=73 truncated=False bug_in_packet=True
RUN: budget=30  first_deadline=10s
  RULING t=  10.7s  REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE at guard.py:539  [suite runs so far: 41]
RESULT: budget=30 status=refused elapsed=10.7s suite_runs=41 of 73 candidates
  summary='REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py). teach it once: ...'
```

Control, `... cut_untruncated.py ./fixture_cut_none none` (`cut_none.out`): `status=repaired elapsed=20.3s suite_runs=74`, `+ if v >= limit:`.

32 of 73 candidates, the bug line among them, were never tried; the byte handed to the law said REFUTED and not CAPPED; the law ruled HARVEST_COUNTEREXAMPLE correctly on that byte; the user is told to teach a class they already have. `GuardReport.summary` (`guard.py:69`) only recognises a budget stop by the substring `"budget exhausted"` in the hint, which this path never writes. This is the same misdiagnosis the 0.11/0.12 CHANGELOG entries fixed for the escalation clock ("blaming the vocabulary sends the user to write a rule they already have"), still open for the first-pass clock.

### F5. The BUILT+CAPPED message is written with a real repair in hand, and every caller throws it away

Command: `nice -n 15 .venv/bin/python timeout.py 300 .venv/bin/python msg_demo.py ./fixture_msg` (`msg_demo.out`). Part A calls `loop.repair()` directly with a 6 s deadline on a 75-line fixture whose bug is ranked first:

```
OBSERVATIONS: 72; rank of the bug line = 0 (0 = tried first)
== A. loop.repair(deadline=t+6s) — the law rules on BUILT+CAPPED ==
  GREEN  t=   1.0s  suite run #1 passed
  RULING t=   6.3s      BUILT+CAPPED (0x21) -> RAISE_BUDGET           at loop.py:217  [suite runs so far: 26]
  res.repaired=False  res.refused=True  res.ambiguous=False
  res.greens=['    if v >= limit:']
  res.suite_runs=26  observations tried (acts_tried)=25 of 72
  res.reason='a candidate passes, but the search was cut short before it could be shown unique — shipping it would be a guess. Raise the budget and re-run (engine law: BUILT+CAPPED -> RAISE_BUDGET)'
```

Part B runs the identical fixture through the door a user uses, at the same clock:

```
== B. guard_once(budget=18) — the same fixture, the report a user sees ==
  RULING t=   6.2s      BUILT+CAPPED (0x21) -> RAISE_BUDGET           at loop.py:217  [suite runs so far: 21]
  RULING t=   6.8s           REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE at guard.py:539  [suite runs so far: 21]
  status=refused  elapsed=6.8s  suite_runs=21
  report.result=None
  report.summary()='REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py). teach it once: docs/TEACHING.md ...'
```

The correct repair `if v >= limit:` was found, proven green twice, handed to the law, ruled RAISE_BUDGET, and then discarded — and the user is told the fault is outside the vocabulary. Part C shows why: no caller reads `.reason` except on the `.ambiguous` branch, and none reads `.greens` at all.

```
== C. every caller of repair()/guard_once(), and the fields it reads ==
  cli.py:83:     return 0 if result.repaired else 2
  coracle.py:762:         if result.repaired:
  coracle.py:766:         if result.ambiguous:
  coracle.py:769:                                hint=result.reason, attempts=attempts)
  guard.py:520:         if result.repaired:
  guard.py:525:         if result.ambiguous:                     # engine law: BUILT+AMB -> ADD_STATE
  guard.py:600:             if result.repaired:
  guard.py:606:             if result.ambiguous:
  javaoracle.py:215:         if result.repaired:
  javaoracle.py:218:         if result.ambiguous:

  grep -rn 'search was cut' src tests docs:
  /Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py:240: f"a candidate passes, but the search was cut short before it "
```

The message exists in exactly one place and no test, doc, or caller pins it. The one caller that would print `result.summary()` — `fluidfix repair` (`cli.py:77-83`) — passes no `deadline`, so `_rule(capped=True)` cannot fire there at all.

### F6. The first-pass/escalation split is a code decision, and its wording disagrees with itself

- `guard.py:468`: `first_deadline = t0 + budget / 3 if budget else None` — the split.
- `guard.py:452-453` (`guard_once` docstring): "the first pass may spend at most **half** of it".
- `cli.py:651` (`--budget` help): "the first pass gets at most **a third**".
- `tests/test_span_edits.py:195`: "With --budget the first pass is cut at **half**".
- `docs/SCALE.md:138-139`: round 2 "half/half", round 3 "split fixed (1/3 + rest)" — the /3 came from the v0.7.1 span-bench measurement (`git log -S'budget / 3'` and `-S'most half of it'` both return f5838ea, which introduced both in the same commit).

The law owns one bit (CAPPED) and one act (RAISE_BUDGET): "a budget truncated the search; raise it". How much to raise, where the clock is split, and how the raise is spent (packet 110 -> 990 -> unbounded at `guard.py:578-583`; the `file_share` half-cap at 591-592; `--escalate-budget` default 600 at `guard.py:443`; `budget / 3` at 468) are all constants in the body, chosen from measurements (SCALE.md rounds 1-4), not ruled. That is consistent with the engine law's vocabulary — it has no bit for "how much" — so this is an actuation the law cannot own today; it is not a wrong ruling. It IS a wording defect: three of the four places describing the split disagree with the code, and F7 shows the split that actually decides the outcome (`/2` on the remaining clock) is documented nowhere.

## 4. Lanes

Law: engine (`src/fluidfix/engine.py`), as consulted from `loop.py:217` and `guard.py:491/539/612/618`.

Reached in this work (every ruling logged by the `decide` wrapper — `fixture_*/rulings.json`, `cut_*.out`, `msg_demo.out`):

| byte | bits | ruling | where | which run |
|---|---|---|---|---|
| 0x01 | BUILT | SHIP | loop.py:217 | sweeps 350, 400, 450, 600, 750, 900; cut_none |
| 0x21 | BUILT+CAPPED | RAISE_BUDGET | loop.py:217 | sweeps 300, 325; msg_demo A and B |
| 0x60 | CAPPED+REFUTED | RAISE_BUDGET | guard.py:539 | all nine sweep runs (packet always truncated) |
| 0x40 | REFUTED | HARVEST_COUNTEREXAMPLE | guard.py:539 | cut_b30, msg_demo B (untruncated packet, clock cut) |
| 0x40 | REFUTED | HARVEST_COUNTEREXAMPLE | guard.py:612/618 | sweeps 150, 300, 325; cut_b30; msg_demo B |

Never reached, and why:

- **0x20 CAPPED alone** at the gate: needs a truncated packet with NO candidate tried in the first pass (`acts0` False) — the fixture's packet always yields 110 candidates. Reachable with a truncated packet whose sampled lines carry no kinds.
- **0x03 / 0x23 BUILT+AMB(+CAPPED) -> ADD_STATE**: needs two greens at different sites; this fixture has one repair. Pinned elsewhere (`tests/test_span_edits.py::test_two_green_spans_refuse_ambiguous`, target 04).
- **0x10 HIDDEN -> CHANGE_GRANULARITY**: needs a green that goes red on re-check; the suite here is deterministic (target 05).
- **0x04 UNREAD -> ADD_MATERIAL** (`guard.py:491`): needs no candidate files AND no pytest-cov; the fixture always names `mod.py`.
- **Bytes with NOTWIN or SELF**: never packed by the body anywhere (targets 09/02).
- **The 8 BUILT+AMB+UNREAD+CAPPED bytes ruled RAISE_BUDGET** (F1): the body packs UNREAD only alone, so this whole family is dead today.
- **The "escalation budget exhausted" hint** (`guard.py:556-572`) was never produced in any run: it is emitted only at the top of the per-file loop for a NEXT file, and this fixture has one file — so the escalation clock cut at 150, 300 and 325 surfaced as REFUTED instead. `GuardReport.summary`'s two budget-aware branches (`guard.py:71-95`) are gated on the substring `"budget exhausted"` and were therefore never taken either.

## 5. Potential

- **Measuring CAPPED from a deadline cut** (F4): on `cut_untruncated.py` it is the difference between a 10.7 s refusal that blames the vocabulary and, at the budget the message would ask for, a 20.3 s repair — measured. On the target fixture, at 150, 300 and 325 the true situation was CAPPED and the report said REFUTED; the correct hint would have named a budget >= ~350 s, which repairs. How often this shape occurs on real repos: **unmeasured**.
- **Delivering the BUILT+CAPPED message** (F5): measured on `msg_demo.py` — the guard held a suite-green, twice-confirmed repair (`if v >= limit:`) and reported "fault is outside the taught vocabulary". Surfacing `res.reason` and `res.greens` costs one field on `GuardReport` and turns a wrong diagnosis into an actionable one. Frequency on real repos: **unmeasured**.
- **The `file_share` half-cap** (F7): worth 2x the user's budget on any single-candidate-file repair. Skipping the cap when `len(all_files) == 1` (nothing can be starved) would move this fixture's threshold from the measured 325/350 bracket down to the `t1 + W` band the same script computes, `[180 s .. 240 s]` — i.e. roughly **45% less budget for the same repair**, measured on this fixture. On multi-file repos the cap is doing real work and should stay; **unmeasured** there.
- **Raising the budget by a measured amount rather than a constant**: the law can only say RAISE_BUDGET; the body raises by fixed steps. What the raise should be is a function of candidates-per-second and candidates remaining, both of which the loop already counts (`res.suite_runs`, `len(observations)`), so the observation is measurable today. The number here: escalation needs 804 runs at ~0.20-0.26 s = 156-207 s measured across six completed runs, i.e. the raise needed is knowable before the clock is spent. Worth beyond this fixture: **unmeasured**.
- **The pinned handover test exercises no first-pass cut on this machine**: the first pass finishes alone in 23.4-33.3 s at every budget from 150 to 900, so `first_deadline = budget/3` never fires. A fixture that actually tests the `budget/3` split needs first-pass work > budget/3 — e.g. a taught class with >= 32 candidates per sampled line. Building one: **unmeasured**.

## 6. Defects

1. **Observation — a first-pass clock cut is not packed as CAPPED.** `guard.py:508/538` read only `packet.truncated` and the candidate-file-list truncation; `loop.py:272/291` return a deadline reason nobody reads. Evidence: F4, `cut_b30.out` — 41 of 73 candidates tried, byte 0x40, ruling HARVEST_COUNTEREXAMPLE (correct for 0x40), report "fault is outside the taught vocabulary"; the control run repairs. The ruling was right on the byte it was given; the byte was wrong.
2. **Observation/wording — an escalation clock cut with ONE candidate file is reported as REFUTED.** `guard.py:556-572` emits the "escalation budget exhausted" hint only before a NEXT file, so with one file `guard.py:611-616` writes the REFUTED hint instead, and `GuardReport.summary`'s budget branches never fire. Evidence: F3, `sweep_150.out` / `sweep_300.out` / `sweep_325.out` — cut at 92.2 / 162.0 / 175.2 s, hint "every generated candidate was rejected", summary "fault is outside the taught vocabulary". `sweep_325.out` also shows `attempts logged=128` while 578 escalation candidates were rejected (the 64-per-`repair()` log cap).
3. **Actuation — the RAISE_BUDGET ruling from `_rule(capped=True)` is discarded by every caller.** `guard.py:520-529` and `600-610`, `coracle.py:762-769`, `javaoracle.py:215-221` inspect only `.repaired` / `.ambiguous`; the final `GuardReport` (`guard.py:619`) carries no `result`, so `reason` and `greens` are gone. Evidence: F5, `msg_demo.out` — the law ruled `BUILT+CAPPED (0x21) -> RAISE_BUDGET` with `res.greens=['    if v >= limit:']`, and `report.result=None`, `report.summary()` = "fault is outside the taught vocabulary". No test pins the message (`grep -rn 'search was cut' src tests docs` -> `loop.py:240` only). **This is the highest-value defect found: the law's ruling is correct, complete, and never delivered.**
4. **Actuation — the `file_share` half-cap is applied when there is nothing to starve.** `guard.py:591-592` halves the remaining clock for every file including a lone one, so `--budget` buys half what its own help text ("cap for the WHOLE guard pass", `cli.py:649`) promises. Evidence: F7, `threshold.out` — every refused run ended within 0.5 s of the `file_share/2` prediction and none was ever cut by `total_deadline`. Classified as actuation, not ruling: the law said RAISE_BUDGET and the body chose how much of the raise to spend.
5. **Wording — the split is described three different ways.** `guard.py:452-453` "at most half" vs `guard.py:468` `budget / 3` vs `cli.py:651` "a third" vs `tests/test_span_edits.py:195` "cut at half". Evidence: F6.
6. **Wording — stale measurement in the pinned test and CHANGELOG.** `tests/test_span_edits.py:216-223` and `CHANGELOG.md:48-50` say "at 450 the first pass is cut at 150s and ESCALATION repairs at 173s ... At 600 the first pass finishes on its own and escalation is never reached." Measured today across nine budgets: the first pass finishes alone in 23.4-33.3 s at EVERY budget (it is never cut), and escalation IS reached at every budget including 600 and 900 — `result.reason` carries the escalation-only `", depth-first"` suffix in all six repaired runs. Whether the 2026-09-05 machine was ~5x slower or the code changed since: **unmeasured**.
7. **Wording — stale comment.** `tests/test_engine_fusion.py:74-76` says the fillers "yield NO observer kinds"; they yield kind 12 on every one of the 800 lines (F2), which is what creates the 802-observation grind the budget test depends on.
8. **Ruling: none found.** Every byte the body handed the law across nine sweep runs, two `cut_untruncated` runs and the `msg_demo` runs was ruled exactly as the docstring specifies (F1). Every wrong outcome above traces to a bit not measured, a ruling not actuated, or a sentence that no longer matches the code.

## 7. Verdict

BUILT+CAPPED -> RAISE_BUDGET is correct on every one of the 256 bytes and was reached live at budgets 300 and 325, but the repair it protects is thrown away by every caller (`msg_demo.out`: a twice-confirmed green reported as "fault is outside the taught vocabulary"), and the 325/350 threshold measured on this fixture is set not by `--budget` but by the undocumented `file_share/2` cap at `guard.py:591-592` — four actuation/observation defects and three wording defects, zero wrong rulings.
