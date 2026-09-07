# 02-engine-lane-reach

## 1. Target

Find every `decide(situation(...))` call in the body, enumerate which of the 256 engine-law situations the body can actually construct, and list the lanes it can never reach together with the observation each would need.

## 2. Method

Read, in `/Users/kanchetidevieswar/neo/fluidfix/`:

- `src/fluidfix/engine.py` (the law, `BITS`, `ACTS`, the docstring spec)
- `src/fluidfix/loop.py` lines 190-235 (`_rule()`) and 352-400 (the HIDDEN re-check)
- `src/fluidfix/guard.py` lines 118-200 (`find_candidate_files`), 431-437 (`_has_pytest_cov`), 478-560 and 598-625 (the four guard call sites, `capped0` / `acts0`)
- `src/fluidfix/cli.py` lines 460-480 (`selfcheck`)

Call sites were located with:

```
$ cd /Users/kanchetidevieswar/neo/fluidfix && grep -rn "decide(" src/fluidfix/*.py | grep -v "^src/fluidfix/engine.py"
src/fluidfix/cli.py:474:    rule_bad = sum(decide(situation(**{k: True})) != v for k, v in rulings.items())
src/fluidfix/guard.py:491:        if decide(situation(UNREAD=True)) == "ADD_MATERIAL":
src/fluidfix/guard.py:539:    if escalate and decide(situation(CAPPED=capped0, REFUTED=acts0)) == "RAISE_BUDGET":
src/fluidfix/guard.py:612:                decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":
src/fluidfix/guard.py:618:            decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":
src/fluidfix/loop.py:217:        ruling = decide(situation(BUILT=True,
src/fluidfix/loop.py:391:                            ruling = decide(situation(HIDDEN=True))
```

`acts.py` contains none (`grep -c "decide(" src/fluidfix/acts.py` -> `0`).

Scripts in this directory (all rerunnable):

| script | what it does |
| --- | --- |
| `enumerate_reach.py` | static: packs every combination each call site's free bits allow, rules on each, prints the reach table |
| `reach_dynamic.py` | drives `loop.repair()` with a scripted stub oracle to confirm `BUILT+CAPPED`, `HIDDEN`, and that `BUILT+AMB+CAPPED` is never constructed |
| `reach_unread.py` | drives `guard.guard_once()` with a stub oracle to confirm the `UNREAD` lane, with a control |
| `unreached_lanes.py` | for each unreached act/bit, what observation would be needed, counted over all 256 |
| `log_decide_plugin.py` + `summarize_log.py` | pytest plugin that logs every `decide()` the body makes during a real test run, without editing `src/` or `tests/` |
| `run.sh` | `nice -n 15` + hard timeout (see note below) |

**Note on the brief's `timeout` requirement.** This machine has no GNU `timeout`:

```
$ which timeout gtimeout
timeout not found
gtimeout not found
```

`run.sh` supplies the equivalent (`nice -n 15 perl -e 'alarm shift; exec @ARGV' <secs> <cmd>`). Every run below went through it.

Prior-run artifacts in this directory (`enumerate_reach.out`, `reach_dynamic.out`, `decide_log_run1/2.jsonl`) were re-verified, not assumed. `enumerate_reach.py` was re-run and diffed byte-for-byte against the stored output:

```
$ ./run.sh 300 <venv>/bin/python enumerate_reach.py > enumerate_reach_verify.out
$ diff enumerate_reach.out enumerate_reach_verify.out && echo "REPRODUCES IDENTICALLY"
REPRODUCES IDENTICALLY
```

## 3. Findings

### Finding 1 — the body has 7 call sites, not 6; the 7th is in `cli.py` and is verification, not decision

The prior run's static table listed six sites (the three files the target names). The full grep above finds a seventh, `cli.py:474`, inside `selfcheck`. It is not a repair decision — it re-derives five single-bit rulings to check the vendored law has not drifted — but it is a real `decide(situation(...))` in `src/fluidfix/`, and it appears in execution logs. Observed:

```
$ ./run.sh 120 <venv>/bin/python summarize_log.py decide_log_run1.jsonl decide_log_run2.jsonl decide_log_full_partial.jsonl decide_log_run3.jsonl
body consultations: site, x, bits -> act (count)
  cli.py:474     x=  1 BUILT                -> SHIP                   x2
  cli.py:474     x=  2 AMB                  -> ADD_STATE              x2
  cli.py:474     x=  4 UNREAD               -> ADD_MATERIAL           x2
  cli.py:474     x= 32 CAPPED               -> RAISE_BUDGET           x2
  cli.py:474     x= 64 REFUTED              -> HARVEST_COUNTEREXAMPLE x2
```

`x=2` (AMB alone) is constructed **only** here; the repair path never builds it.

### Finding 2 — the body can construct 9 of 256 situations (3.5%), and obtain 6 of 8 acts

```
$ ./run.sh 300 <venv>/bin/python enumerate_reach.py
distinct situations packed:    10/256
distinct situations reachable: 9/256 -> [0, 1, 3, 4, 16, 32, 33, 64, 96]
```

```
$ ./run.sh 300 <venv>/bin/python unreached_lanes.py
=== 5. coverage of the law's ruling surface ===
  SHIP                    2/  4 situations reachable
  ADD_STATE               1/113 situations reachable
  ADD_MATERIAL            1/ 64 situations reachable
  RESHAPE                 0/ 17 situations reachable
  CHANGE_GRANULARITY      1/ 16 situations reachable
  RAISE_BUDGET            3/ 23 situations reachable
  HARVEST_COUNTEREXAMPLE  1/  4 situations reachable
  AUTHOR_SUCCESSOR        0/ 15 situations reachable
  TOTAL                  9/256 situations reachable (3.5%); 6/8 acts obtainable
```

### Finding 3 — NOTWIN is a strict necessary condition for BOTH unreached acts; SELF is necessary for neither

This is the single most consequential measurement here. Of the 32 situations ruling `RESHAPE` or `AUTHOR_SUCCESSOR`, every one has NOTWIN set:

```
$ ./run.sh 60 <venv>/bin/python -c "..."   # saved as notwin_necessity.out
RESHAPE count 17 | all have NOTWIN set: True | all have SELF set: False
AUTHOR_SUCCESSOR count 15 | all have NOTWIN set: True | all have SELF set: False
situations with NOTWIN clear that rule RESHAPE or AUTHOR_SUCCESSOR: []
```

And the marginal value of each bit, starting from today's 9 situations:

```
$ ./run.sh 300 <venv>/bin/python unreached_lanes.py
=== 3. marginal value of making one bit measurable, from today's 9 ===
  +NOTWIN   -> + 9 situations, new acts: ['AUTHOR_SUCCESSOR', 'RESHAPE']
  +SELF     -> + 9 situations, new acts: none
  +BUILT    -> + 4 situations, new acts: none
  +AMB      -> + 7 situations, new acts: none
  +UNREAD   -> + 7 situations, new acts: none
  +HIDDEN   -> + 7 situations, new acts: none
  +CAPPED   -> + 3 situations, new acts: none
  +REFUTED  -> + 5 situations, new acts: none
```

SELF flips the law's ruling on only 2 of 128 base situations, and one of those two is itself NOTWIN-gated:

```
  SELF    flips the ruling on   2 of 128 base situations; acts reachable ONLY once SELF can be set: none
      x=  7 BUILT+AMB+UNREAD         ADD_STATE              -> with SELF: RAISE_BUDGET
      x=  8 NOTWIN                   RESHAPE                -> with SELF: AUTHOR_SUCCESSOR
```

NOTWIN flips 47 of 128. **One missing observation, NOTWIN, accounts for both of the law's two unobtainable acts.**

### Finding 4 — the UNREAD lane (`guard.py:491`) is genuinely reachable and correctly gated; it had never been exercised

No test in the suite reaches it (Finding 6). I drove `guard_once()` with a stub oracle whose interpreter genuinely lacks pytest-cov (`/usr/bin/python3`; the project venv has pytest_cov 7.1.0), plus a control on the venv interpreter:

```
$ ./run.sh 300 <venv>/bin/python reach_unread.py
--- pytest-cov ABSENT  (expected: UNREAD asked)
  find_candidate_files       : []  (empty => `not candidates` True)
  _has_pytest_cov(oracle)    : False
  law asked                  : [(4, 'UNREAD', 'ADD_MATERIAL'), (0, '<empty>', 'SHIP')]
  hint                       : 'pytest-cov is not installed in the target interpreter, so coverage-based localisation was unavailable - install it (/usr/bin/python3 -m pip install py...'

--- pytest-cov PRESENT (expected: UNREAD not asked)
  _has_pytest_cov(oracle)    : True
  law asked                  : [(0, '<empty>', 'SHIP')]
  hint                       : ''

  lane guard.py:491 is REACHABLE and gated by the measurement: True
```

The bit is measured from a real fact and the ruling reaches the user's hint text.

### Finding 5 — `BUILT+CAPPED` and `HIDDEN` are reachable; `BUILT+AMB+CAPPED` (x=35) is provably never constructed

```
$ ./run.sh 300 <venv>/bin/python reach_dynamic.py
=== A. BUILT+CAPPED via deadline between kinds ===
  law asked: [(33, 'BUILT+CAPPED', 'RAISE_BUDGET')]
  file untouched after refusal: True

=== B. HIDDEN via one-run green, re-check red ===
  law asked: [(16, 'HIDDEN', 'CHANGE_GRANULARITY')]
  tried_log why: 'green on one run, RED on re-check - the suite does not hold still here, so a single run cannot judge this candidate (eng...'

=== C. AMB proven AFTER the deadline expired: is x=35 ever asked? ===
  law asked: [(3, 'BUILT+AMB', 'ADD_STATE')]
  x=35 asked: False   (law on x=35 would rule ADD_STATE, on x=3 rules ADD_STATE)
```

x=35 is the one combination `loop.py:217`'s free bits can *pack* but control flow can never *reach*: once AMB is proven the loop breaks and rules with `capped=False`, and before it is proven `sites <= 1` so AMB is False. **This is harmless**: the law rules `ADD_STATE` on both x=3 and x=35, so the unreachable packing changes no outcome.

### Finding 6 — across 45 tests in which the body consults the law, the repair path constructs only 5 distinct situations

```
$ ./run.sh 120 <venv>/bin/python summarize_log.py decide_log_run1.jsonl decide_log_run2.jsonl decide_log_full_partial.jsonl decide_log_run3.jsonl
records: 140  from the body: 90  direct from tests: 50
tests during which the BODY consulted the law: 45
  guard.py:539   x=  0 <empty>              -> SHIP                   x5
  guard.py:539   x= 64 REFUTED              -> HARVEST_COUNTEREXAMPLE x7
  guard.py:539   x= 96 CAPPED+REFUTED       -> RAISE_BUDGET           x3
  guard.py:618   x= 64 REFUTED              -> HARVEST_COUNTEREXAMPLE x7
  loop.py:217    x=  1 BUILT                -> SHIP                   x53
  loop.py:217    x=  3 BUILT+AMB            -> ADD_STATE              x5
distinct situations the body constructed: [0, 1, 2, 3, 4, 32, 64, 96]
distinct sites: ['cli.py:474', 'guard.py:539', 'guard.py:618', 'loop.py:217']
```

Repair-path situations observed under test: **{0, 1, 3, 64, 96}** — five. `x=2`, `x=4` and `x=32` in that list come from `cli.py:474` only. `loop.py:391` (HIDDEN) and `guard.py:491` (UNREAD) were reached by no test; I reached both with the drivers above.

**Full-suite caveat.** The whole suite does not fit the brief's 300s cap:

```
$ ... run.sh 290 <venv>/bin/python -m pytest -q -p log_decide_plugin tests/
exit=142                      # 128+14 = SIGALRM
........................................................................ [ 36%]
```

So the 45 tests above are the union of four bounded runs (`decide_log_run1/2/3.jsonl` + the 36% partial), not one complete pass. The remaining test files were **not** measured; whether they construct any further situation is **unmeasured**.

### Finding 7 — `x=32` (CAPPED alone) at `guard.py:539` is constructible but was never observed

`capped0 = packet.truncated or len(all_files) > len(candidates)` (guard.py:508, 538) and `acts0 = any(result.acts_tried)` (guard.py:519) are independent, so all four combinations {0, 32, 64, 96} are constructible. Runs observed 0, 64 and 96 (Finding 6) but never 32. The observation that produces it: coverage implicates more files than the first-pass cap admits, **and** no candidate class matched any line in the files actually tried. I did not construct it; its reachability here is static reasoning from the two assignments, and dynamically **unmeasured**.

### Finding 8 — the law's own docstring says HIDDEN is never set; `loop.py` has set it since 0.13.0

`src/fluidfix/engine.py:27`:

> `NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set`

But `src/fluidfix/loop.py:391` is `ruling = decide(situation(HIDDEN=True))`, and Finding 5B reaches it. `loop.py:357-370` even says so in the opposite direction: *"HIDDEN, ACTUATED"* and *"the first of the three lanes fluidfix never measured (NOTWIN, HIDDEN, SELF) to turn out to matter"*. The two texts contradict each other. Git dates them:

```
$ git log --oneline -S 'NOTWIN, HIDDEN and SELF are not yet measured' -- src/fluidfix/engine.py
60cc98c 0.6.0: the engine law fused into the guard - ...
$ git log --oneline -S 'situation(HIDDEN=True)' -- src/fluidfix/loop.py
b67ab83 0.13.0: a flaky oracle, the lane that already ruled on it, and C#
```

The docstring text is from 0.6.0; the measurement arrived at 0.13.0 and the docstring was not updated.

### Finding 9 — `selfcheck` verifies 5 rulings and reports "the rulings the guard depends on", but the guard now depends on 6

`cli.py:472` lists `BUILT, AMB, UNREAD, CAPPED, REFUTED` — HIDDEN is absent, though `loop.py:391` branches its user-visible `why` text on the HIDDEN ruling.

```
$ ./run.sh 120 <venv>/bin/fluidfix selfcheck | grep -i "engine law"
engine law fingerprint (sha256 48bf50bff36a2cc9, 1555 chars): verbatim
engine law rulings the guard depends on:      5/5
```

The `5/5` is true of the five it checks; the label "the rulings the guard depends on" is what overstates. If the vendored law ever drifted on x=16, selfcheck would not notice.

## 4. Lanes

**Reached** (9 situations, 6 acts):

| x | bits | ruling | site | how confirmed |
| --- | --- | --- | --- | --- |
| 0 | (empty) | SHIP | guard.py:539 | test suite (F6) |
| 1 | BUILT | SHIP | loop.py:217 | test suite (F6) |
| 3 | BUILT+AMB | ADD_STATE | loop.py:217 | test suite (F6) |
| 4 | UNREAD | ADD_MATERIAL | guard.py:491 | `reach_unread.py` (F4) |
| 16 | HIDDEN | CHANGE_GRANULARITY | loop.py:391 | `reach_dynamic.py` B (F5) |
| 32 | CAPPED | RAISE_BUDGET | guard.py:539 | static only (F7) |
| 33 | BUILT+CAPPED | RAISE_BUDGET | loop.py:217 | `reach_dynamic.py` A (F5) |
| 64 | REFUTED | HARVEST_COUNTEREXAMPLE | guard.py:539/612/618 | test suite (F6) |
| 96 | CAPPED+REFUTED | RAISE_BUDGET | guard.py:539 | test suite (F6) |

Plus `cli.py:474` (verification only): x = 1, 2, 4, 32, 64.

**Never reached** (247 situations, 2 acts):

- **RESHAPE (17 situations) and AUTHOR_SUCCESSOR (15).** Unreachable for exactly one reason: both require NOTWIN, and nothing in the body sets NOTWIN. No actuation, branch or if-statement is missing — the **observation** is (Finding 3).
- **Every situation with NOTWIN or SELF set.** Same cause.
- **The multi-bit interiors** of ADD_STATE (1 of 113 reached), ADD_MATERIAL (1 of 64) and CHANGE_GRANULARITY (1 of 16). The body asks each site a *narrow* question — `loop.py:217` only ever offers BUILT/AMB/CAPPED, `guard.py:539` only CAPPED/REFUTED — so bits measured at one site are never presented at another. E.g. the body can measure UNREAD (guard.py:491) and CAPPED (guard.py:539) in the same pass, but never packs them into one situation.
- **x=35 (BUILT+AMB+CAPPED)** is packable at `loop.py:217` but unreachable by control flow, and harmless: the law rules ADD_STATE on it and on x=3 alike (Finding 5C).

**What each unreached lane would need**, stated honestly:

- RESHAPE / AUTHOR_SUCCESSOR: an observation for NOTWIN. **The repo contains no definition of NOTWIN.** `grep -rn "NOTWIN" docs/ src/ CHANGELOG.md README.md tests/` returns only the bit name in `BITS`, the stale docstring line, a comment in `loop.py:367`, and a bit-name list in `tests/test_engine_fusion.py:230`. What NOTWIN should measure is therefore **unspecified**, not merely unmeasured, and I will not invent it here.
- SELF: reaching it adds 9 situations and **zero** new acts (Finding 3). Its design is target 09's question.
- The multi-bit interiors: they need no new bit, only a wider `situation(...)` at an existing site — which is an actuation/plumbing change, not a decision.

## 5. Potential

**Measured:**

- The body reaches **9 of 256 situations (3.5%)** and **6 of 8 acts** (Finding 2).
- Making NOTWIN measurable would add **9 situations and 2 acts** — the only single bit that adds any act at all (Finding 3).
- Making SELF measurable would add **9 situations and 0 acts** (Finding 3). On today's evidence SELF is the lower-value of the two unset bits by a wide margin, and target 09 should weigh it against that.
- Widening `loop.py:217`'s question is the cheapest untapped surface by count: ADD_STATE is the law's largest act at **113 of 256 situations**, of which the body reaches **1**.

**Unmeasured:**

- What NOTWIN, once defined and measured, would be worth in *repairs* — extra fixes, avoided false accepts, suite runs saved — is **unmeasured**. I measured ruling-surface reach, not repair outcomes.
- Whether any of the ~64% of the test suite I could not run within the 300s cap constructs a further situation is **unmeasured** (Finding 6).
- Whether `x=32` at `guard.py:539` occurs on any real repo is **unmeasured** (Finding 7).

## 6. Defects

**Two, both wording. No ruling defect found.**

1. **Wording — `src/fluidfix/engine.py:27`.** The law's docstring states NOTWIN, HIDDEN and SELF "are never set". HIDDEN has been set by `loop.py:391` since commit b67ab83 (0.13.0), and I reached it (Finding 5B, Finding 8). The docstring is the module's specification, so a reader auditing which lanes are live is misinformed by the primary source. Not a mismeasured bit — HIDDEN's measurement is sound and its ruling correct — and not a missing actuation. **Fix belongs in the docstring; I did not make it** (the brief forbids editing `src/`).

2. **Wording — `src/fluidfix/cli.py:475`.** `selfcheck` prints "engine law rulings the guard depends on: 5/5" while checking five of the six rulings the body actually consults; HIDDEN (x=16) is omitted from the `rulings` dict at `cli.py:472` (Finding 9). The count is honest; the label is not. Consequence is narrow but real: drift in the law's x=16 ruling would pass selfcheck silently.

**Explicitly not defects:**

- x=35 being packable-but-unreachable at `loop.py:217` is not a defect: the law rules ADD_STATE on x=35 and x=3 alike, so no outcome depends on it (Finding 5C).
- The law ruling `SHIP` on x=0 at the `guard.py:539` escalation gate is not a wrong outcome. The body tests `== "RAISE_BUDGET"` only, so SHIP-at-a-refusal is read as "do not escalate" and nothing ships. The law ruled on the situation it was given — an empty evidence byte — and the body actuated only the lane it asked about.
- RESHAPE and AUTHOR_SUCCESSOR being unreachable is a documented limitation with a named cause (NOTWIN unmeasured), not a wrong outcome.

## 7. Verdict

The body constructs 9 of 256 engine-law situations and obtains 6 of 8 acts; the two it never obtains, RESHAPE and AUTHOR_SUCCESSOR, are blocked by exactly one unmeasured and repo-undefined observation, NOTWIN, while SELF would add no act at all — and the only defects found are two wording ones (engine.py:27 and cli.py:475 both under-report the now-live HIDDEN lane), with zero wrong rulings.
