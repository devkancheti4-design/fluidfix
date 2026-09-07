# 06-engine-capped-budget — REPORT

## 1. Target

Sweep `--budget` (150..900) on the fixture of `tests/test_span_edits.py::test_budget_hands_first_pass_over_to_escalation`; confirm BUILT+CAPPED -> RAISE_BUDGET and its message; find the threshold; decide whether the first-pass/escalation split is a code decision.

## 2. Method

Everything I wrote is in `/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/06-engine-capped-budget/`. Nothing under `src/`, `tests/`, `docs/` was touched; no git state changed. macOS has no coreutils `timeout`, so `timeout.py` (kills the process group after N s, exit 124) stands in for `timeout 300`. Every run is `nice -n 15 <venv python> timeout.py 300 <venv python> <script>`, executed strictly one at a time by `run_queue.sh` (`queue.log` has the start/end stamps). Machine: load average 2.86 at start, shared with 49 other agents — every wall-clock number below is from this loaded machine.

Read (absolute root `/Users/kanchetidevieswar/neo/fluidfix/`): `src/fluidfix/engine.py`; `src/fluidfix/loop.py` (`_rule` 193-243; its call sites 272, 291, 424); `src/fluidfix/guard.py` (`guard_once` 442-621: `first_deadline` 468, `capped0` 485/508/538, the gate 539, escalation 540-616, `GuardReport.summary` 57-101); `src/fluidfix/localize.py` (`Packet.truncated` 41, filter/stride 160-175); `src/fluidfix/oracle.py:185-241` (`check`); `src/fluidfix/cli.py` (60-82 single-file `repair`, 649-653 `--budget` help); `src/fluidfix/coracle.py:755-771`; `src/fluidfix/javaoracle.py:212-221`; `tests/test_span_edits.py:172-226`; `tests/test_engine_fusion.py:20-30, 71-105, 205-241`; `CHANGELOG.md` (0.14.0, 0.7.1); `docs/SCALE.md:125-150`; read-only `git log -S`.

Scripts (rerunnable, next to this report):

- `static_analysis.py` -> `static_analysis.out`: the law's ruling on every byte the body can pack at `loop.py:217` and `guard.py:539`; all 256 inputs split by the CAPPED bit; the fixture's search-space arithmetic.
- `sweep_budget.py <B> <dir>` -> `sweep_<B>.out`, `fixture_<B>/rulings.json`: rebuilds the fixture verbatim (same 800 filler lines, same pad search as the test), wraps `engine.decide`/`loop.decide` to log every ruling with its call site, counts every `Oracle.check`, runs `guard_once(oracle, MechanicalObserver(), budget=B)`.
- `cut_untruncated.py <dir> <B|none>` -> `cut_b30.out`, `cut_none.out`: the same bug in a 76-line file whose first-pass packet is NOT truncated.
- `tabulate.py`: the sweep table, regenerated from `fixture_*/rulings.json`.
- `run_queue.sh`: the exact sequence run.

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

The 16 CAPPED inputs ruled RAISE_BUDGET are the 8 "clean" ones (CAPPED with any of BUILT/REFUTED/SELF: 0x20 0x21 0x60 0x61 0xa0 0xa1 0xe0 0xe1) plus 8 of the shape BUILT+AMB+UNREAD+CAPPED(+HIDDEN)(+REFUTED)(+SELF) (0x27 0x37 0x67 0x77 0xa7 0xb7 0xe7 0xf7). So BUILT+AMB+CAPPED -> ADD_STATE and BUILT+UNREAD+CAPPED -> ADD_MATERIAL, but BUILT+AMB+UNREAD+CAPPED -> RAISE_BUDGET (verified by direct `decide()` calls, transcript in section 6). Those 8 are unreachable today: the body packs UNREAD only alone (`guard.py:491`). Precedence in general is target 07's; I record only what my sweep touches.

Note also that `CAPPED=0, REFUTED=0` at the gate rules SHIP — the byte 0x00 means "nothing happened". The gate at `guard.py:539` compares `== "RAISE_BUDGET"`, so SHIP there simply skips escalation; nothing is shipped (the first pass has no green in that path, since a green returns at `guard.py:518`).

### F2. Fixture arithmetic: the "grind" is 110 + 802 suite runs, and the ranking law puts the bug line at position 400 of 802

Same command, section 2 of `static_analysis.out`:

```
== 2. fixture arithmetic (pad=0, bug at mod.py:403, file has 806 lines) ==
  first pass  (build_packet default max_lines=110): packet lines=110 truncated=True bug_in_packet=False
    observations=110 kinds histogram={12: 109, 1: 1} distinct candidates (= max suite runs, before dedup)=110
  escalation  (max_lines=990, guard.py:578): packet lines=803 truncated=False bug_in_packet=True
    observations=802 kinds histogram={12: 800, 0: 1, 10: 1, 1: 1} distinct candidates=803
    ranking-law position of the bug line among observations: 400 (0 = tried first)
  one suite run (oracle.check, fail-fast --lf path) on this fixture:
    run 1: ok=False 0.33s / run 2: 0.21s / run 3: 0.20s
```

Three consequences. (a) The first pass costs a fixed 110 suite runs (~27-33 s here). (b) Since 0.14.0 the search does not stop at the first green, so escalation ALWAYS costs the full 802 candidates (+2 confirm runs) whatever the ranking does; the ranking's position 400 only decides whether a green exists when a deadline lands. (c) The filler lines are observations at all only because kind 12 (`flipped-boolean`, added in 0.8.0, commit c35ca67) matches `True`; `tests/test_engine_fusion.py:74-76` still says the fillers "yield NO observer kinds ... keeping the suite-run count small" — a stale comment, and the 802-run grind the budget test depends on is an accident of that later kind.

### F3. Budget sweep

SWEEP_TABLE_PLACEHOLDER

### F4. A first-pass DEADLINE cut is not measured as CAPPED (observation defect, masked on the target fixture)

`guard.py:508` and `:538` set `capped0` from `packet.truncated` and from "more candidate files than tried" only. When `repair()` returns because `first_deadline` passed (`loop.py:272/291`, reason `"wall-clock deadline reached mid-search"`), nothing reads that. On the target fixture the packet is truncated anyway, so CAPPED is true for another reason and the gap is invisible. `cut_untruncated.py` removes the mask: same bug, 76-line file, untruncated packet (73 lines), 73 candidates, bug ranked last.

Command: `nice -n 15 python timeout.py 300 python cut_untruncated.py ./fixture_cut_b30 30` (`cut_b30.out`):

```
FIXTURE: 76 lines, bug at mod.py:73, first-pass packet lines=73 truncated=False bug_in_packet=True
RUN: budget=30  first_deadline=10s
  RULING t=  10.7s  REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE at guard.py:539  [suite runs so far: 41]
  RULING t=  10.7s  REFUTED (0x40) -> HARVEST_COUNTEREXAMPLE at guard.py:618  [suite runs so far: 41]
RESULT: budget=30 status=refused elapsed=10.7s suite_runs=41 of 73 candidates
  hint='every generated candidate was rejected by the suite (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) — ...'
  summary='REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py). teach it once: ...'
```

Control, `... cut_untruncated.py ./fixture_cut_none none` (`cut_none.out`): `status=repaired elapsed=20.3s suite_runs=74`, `+ if v >= limit:`.

32 of 73 candidates, the bug line among them, were never tried; the byte handed to the law said REFUTED and not CAPPED; the law ruled HARVEST_COUNTEREXAMPLE correctly on that byte; the user is told the fault is outside the vocabulary and to teach a class they already have. `GuardReport.summary` (guard.py:69) only recognises a budget stop by the substring `"budget exhausted"` in the hint, which this path never writes. This is the same misdiagnosis the 0.11/0.12 CHANGELOG entries fixed for the escalation clock ("blaming the vocabulary sends the user to write a rule they already have"), still open for the first-pass clock.

### F5. The BUILT+CAPPED message exists in `loop.py` but no user-facing path can deliver it

`loop.py:239-242` writes `"a candidate passes, but the search was cut short before it could be shown unique — shipping it would be a guess. Raise the budget and re-run (engine law: BUILT+CAPPED -> RAISE_BUDGET)"` into `res.reason`, with `res.refused=True, res.ambiguous=False, res.greens` non-empty. Every caller inspects only `result.repaired` and `result.ambiguous`: `guard.py:518-529` (first pass), `guard.py:598-610` (escalation), `coracle.py:762-769`, `javaoracle.py:215-221`. A RAISE_BUDGET result therefore falls through to the loop's end, where `any_acts` is true and the hint becomes the REFUTED text (`guard.py:611-620`); the final `GuardReport` (`guard.py:619`) carries no `result`, so `reason` is gone. The one caller that prints `result.summary()` — `fluidfix repair` (`cli.py:77-81`) — passes no `deadline`, so `_rule(capped=True)` cannot fire there. `grep -rn "search was cut" src tests` -> only `src/fluidfix/loop.py:240`: no test pins the message.

MSG_DEMO_PLACEHOLDER

### F6. The first-pass/escalation split is a code decision, and its wording disagrees with itself

- `guard.py:468`: `first_deadline = t0 + budget / 3 if budget else None` — the split.
- `guard.py:453` (guard_once docstring): "the first pass may spend at most **half** of it".
- `cli.py:651` (`--budget` help): "the first pass gets at most **a third**".
- `tests/test_span_edits.py:195`: "With --budget the first pass is cut at **half**".
- `docs/SCALE.md:138-139`: round 2 "half/half", round 3 "split fixed (1/3 + rest)" — the /3 came from the v0.7.1 span-bench measurement (commit f5838ea introduced both `budget / 3` and the "at most half" docstring in the same commit: `git log -S'budget / 3'` and `-S'most half of it'` both return f5838ea).

The law owns one bit (CAPPED) and one act (RAISE_BUDGET): "a budget truncated the search; raise it". How much to raise, where the clock is split, how the raise is spent (packet 110 -> 990 -> unbounded at `guard.py:578-583`; one file gets at most half the remaining clock at `guard.py:591-592`; `--escalate-budget` default 600 at `guard.py:443`; `budget / 3` at 468) are all constants in the body, chosen from measurements (SCALE.md rounds 1-4), not ruled. That is consistent with the engine law's vocabulary — it has no bit for "how much" — so this is an actuation the law cannot own today; it is not a wrong ruling. It IS a wording defect: three of the four places describing the split disagree with the code.

## 4. Lanes

Law: engine (`src/fluidfix/engine.py`), as consulted from `loop.py:217/391` and `guard.py:491/539/612/618`.

Reached in this work (every ruling logged by the `decide` wrapper, see `fixture_*/rulings.json`, `cut_*.out`):

| byte | bits | ruling | where | which run |
|---|---|---|---|---|
| 0x01 | BUILT | SHIP | loop.py:217 | 450, 600, 900, 750, cut_none |
| 0x21 | BUILT+CAPPED | RAISE_BUDGET | loop.py:217 | 300 (escalation clock cut with a green in hand) |
| 0x60 | CAPPED+REFUTED | RAISE_BUDGET | guard.py:539 | every sweep run (packet truncated) |
| 0x40 | REFUTED | HARVEST_COUNTEREXAMPLE | guard.py:539 | cut_b30 (untruncated packet, first pass cut by the clock) |
| 0x40 | REFUTED | HARVEST_COUNTEREXAMPLE | guard.py:612/618 | 150, 300, cut_b30 |

Never reached, and why:

- 0x20 CAPPED alone at the gate: needs a truncated packet with NO candidate tried in the first pass (acts0 False) — the fixture's packet always yields 110 candidates. Reachable with a truncated packet whose sampled lines carry no kinds.
- 0x03 / 0x23 BUILT+AMB(+CAPPED) -> ADD_STATE: needs two different greens; this fixture has one repair. Pinned elsewhere (`tests/test_span_edits.py::test_two_green_spans_refuse_ambiguous`, target 04).
- 0x10 HIDDEN -> CHANGE_GRANULARITY (loop.py:391): needs a green that goes red on re-check; the suite here is deterministic (target 05).
- 0x04 UNREAD -> ADD_MATERIAL (guard.py:491): needs no candidate files AND no pytest-cov; the fixture always names mod.py.
- Bytes with NOTWIN or SELF: never packed by the body (engine.py docstring, targets 09/02).
- The "escalation budget exhausted" hint (`guard.py:556-572`) was never produced: it is emitted only at the top of the per-file loop for a NEXT file, and this fixture has one file, so the escalation clock cut at 150 and 300 surfaced as REFUTED instead (F4/F5).

## 5. Potential

- Measuring CAPPED from a deadline cut (F4): on `cut_untruncated.py` it is the difference between a 10.7 s refusal that blames the vocabulary and (with the budget the message would ask for) a 20.3 s repair — measured. On the target fixture, at budgets 150 and 300 the true situation was CAPPED (escalation clock) and the report said REFUTED; the correct hint would have told the user to raise `--budget` to >= ~400 s, which repairs (450: 209.9 s). How often this happens on real repos: unmeasured.
- Delivering the BUILT+CAPPED message (F5): at budget 300 the guard held a suite-green repair (`if v >= limit:`) and discarded it with "fault is outside the taught vocabulary". A user reading that would teach a class; a user reading loop.py's own message would re-run with more budget and get the repair (450 run). Frequency on real repos: unmeasured.
- Raising the budget by a measured amount rather than a constant: the law can only say RAISE_BUDGET; the body raises by fixed steps (110 -> 990 -> unbounded lines; /3 and /2 clock splits). What the raise should be is a function of candidates-per-second and candidates remaining, both of which the loop already counts (`res.suite_runs`, `len(observations)`), so the observation is measurable today — target 46 has the curve; the number here: on this fixture escalation needs 804 runs at ~0.22 s = ~182 s (measured, 450 run), i.e. the raise needed is knowable before the clock is spent. Worth: unmeasured beyond this fixture.
- The pinned handover (`test_budget_hands_first_pass_over_to_escalation`) exercises no handover on this machine: the first pass finishes alone at ~30 s at every budget >= 150. A fixture whose first pass is cut by `budget/3` needs first-pass work > budget/3, e.g. a taught class with >= 32 candidates per line; unmeasured.

## 6. Defects

1. **Observation — first-pass clock cut not packed as CAPPED** (`guard.py:508/538` only read `packet.truncated` and the file-list truncation; `loop.py:272/291` return a deadline reason nobody reads). Evidence: F4, `cut_b30.out`: 41/73 candidates tried, byte 0x40, ruling HARVEST_COUNTEREXAMPLE (correct for 0x40), report "fault is outside the taught vocabulary"; control run repairs. The ruling was right on the byte it was given; the byte was wrong.
2. **Observation/wording — escalation clock cut with ONE candidate file is reported as REFUTED** (`guard.py:556-572` emits the "escalation budget exhausted" hint only before a NEXT file; `guard.py:611-616` then writes the REFUTED hint). Evidence: F3, `sweep_150.out` — deadline at 92.2 s after 180 escalation runs, no green, hint "every generated candidate was rejected", summary "fault is outside the taught vocabulary", `attempts logged=128` while 288 candidates were rejected (the 64-per-`repair()` log cap; `tried_more` is never surfaced).
3. **Actuation — the RAISE_BUDGET ruling from `_rule(capped=True)` is discarded by every guard** (`guard.py:518-529, 598-610`; `coracle.py:762-769`; `javaoracle.py:215-221` inspect only `.repaired`/`.ambiguous`; final `GuardReport` has no `result`). Evidence: F5, `sweep_300.out`: ruling `BUILT+CAPPED (0x21) -> RAISE_BUDGET` logged at `loop.py:217`, GuardReport status refused with the REFUTED hint; the green candidate is in `result.greens` and gone. No test pins the message (`grep "search was cut"` -> loop.py:240 only).
4. **Wording — the split**: `guard.py:453` "at most half" vs `guard.py:468` `budget / 3` vs `cli.py:651` "a third" vs `tests/test_span_edits.py:195` "cut at half". Evidence: F6.
5. **Wording — stale measurement in the pinned test and CHANGELOG**: `tests/test_span_edits.py:216-223` / `CHANGELOG.md:48-50` say "at 450 the first pass is cut at 150s ... at 600 the first pass finishes on its own and escalation is never reached". Measured today: the first pass finishes alone at 27-33 s at every budget, and escalation IS reached at every budget (packet truncated -> 0x60 -> RAISE_BUDGET). Whether the 2026-09-05 machine was ~5x slower or the code changed: unmeasured.
6. **Wording — stale comment** `tests/test_engine_fusion.py:74-76` ("fillers ... yield NO observer kinds"): they yield kind 12 since 0.8.0 (F2).
7. **Ruling**: none found. Every byte the body handed the law was ruled as the docstring specifies (F1); every wrong outcome above traces to a bit not measured or a ruling not actuated.

## 7. Verdict

VERDICT_PLACEHOLDER
