# 22-pair-observation-design

## 1. Target
How the body could measure the PAIR law's eight observations from data `loop.py` already has; a report-only script that computes the byte from a completed single-edit search on a fixture, and the byte and ruling it produces.

## 2. Method
Read, in full: `src/fluidfix/pair.py`, `src/fluidfix/loop.py`, `src/fluidfix/oracle.py`, `src/fluidfix/localize.py` (`build_packet`), `src/fluidfix/observers.py`, `src/fluidfix/acts.py` (registry, `candidate_cap`, `candidates`), `docs/PAIR_LAW_PROMPT.md`, `tests/test_pair_law.py`; grepped `src/`, `tests/`, `docs/` for `pair_law` (only `src/fluidfix/cli.py:527`, i.e. `selfcheck` — the law is fused, never consulted by the body).

Wrote and ran, all inside this directory:
- `observe_pair.py` — replays `loop.py`'s single-edit enumeration through the same public pieces (`build_packet`, `MechanicalObserver`, `acts.act_for`, `acts.candidates`, `Oracle.run`) and additionally records, per candidate, the failing COUNT and the failing NODE SET; then computes the eight bits with a provenance string each, and calls `pair_law`.
- `reach.py` — which of the eight acts are reachable under each subset of measurable bits.
- `packet_probe.py`, `cache_probe.py` — why `DISJOINT` was observable in one fixture directory and not in a byte-identical one.
- Fixtures under `fixtures/`: `single` (one repairable strictness bug), `vocab` (an `or`/`and` fault outside the taught vocabulary), `twobug` and `pristine` (byte-identical two-bug programs: `x >= t` and `return lo - hi`).

Interpreter: `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python`. Every run prefixed `nice -n 15`. **`timeout(1)` does not exist on this host** (`which timeout` -> not found; `nice -n 15 timeout 300 ...` -> `nice: timeout: No such file or directory`), so each run was bounded by the tool-level timeout plus `Oracle`'s own `subprocess` timeout (120 s) and the script's `budget` deadline (240 s). No `src/`, `tests/`, or `docs/` file was written; no git state changed.

## 3. Findings

### 1. The law is fused but never consulted; the body reports two of its lanes in hand-written prose instead
`pair_law` appears exactly once outside its own module and tests.

```
$ grep -rn "pair_law\|from .pair\|import pair" src/ | grep -v "^src/fluidfix/pair.py"
src/fluidfix/cli.py:527:    from .pair import pair_law as _pair
```

Meanwhile `guard.py` hand-writes the answers to two of the law's lanes as strings — `"REFUSED: fault is outside the taught vocabulary ... register() it once"` (guard.py:101, the law's `TEACH`) and `"REFUSED: ran out of budget before the fault was found — this is a SEARCH limit"` (guard.py:93, the law's `BUDGET`/`CAPPED`).

### 2. Only four of the eight bits are computable from what the body has today, and that makes three of the eight acts algebraically unreachable
`EXHAUSTED`, `CHEAP`, `TAUGHT` and `CAPPED` are derivable now (see finding 3). `PARTIAL`, `DISJOINT`, `COUPLED` are not measured anywhere; `CANCELING` is not measurable before a pair is tried (finding 6).

```
$ /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python reach.py
TODAY (loop.py measures EXHAUSTED/CHEAP/TAUGHT/CAPPED only)
  reachable: {'SINGLE': 4, 'TEACH': 2, 'BUDGET': 1, 'REFUSE': 1, 'CAPPED': 8}
  UNREACHABLE: ['PARTITION', 'PAIR', 'WIDEN']

WITH the failing-count + failing-set measurement (CANCELING still unobservable)
  reachable: {'SINGLE': 32, 'TEACH': 5, 'WIDEN': 4, 'PARTITION': 16, 'PAIR': 2, 'BUDGET': 3, 'REFUSE': 2, 'CAPPED': 64}
  UNREACHABLE: []

acts reachable ONLY when CANCELING can be set: []
byte count per act, all 256: {'SINGLE': 32, 'TEACH': 5, 'WIDEN': 4, 'PARTITION': 16, 'PAIR': 2, 'BUDGET': 3, 'REFUSE': 130, 'CAPPED': 64}
```

The three unreachable acts are exactly the three that do something other than stop: `PARTITION` (16 bytes), `PAIR` (2), `WIDEN` (4).

### 3. The design, bit by bit — where each observation comes from
Column "cost" is extra suite runs beyond what a search already pays.

| bit | source in the body today | cost | status |
|---|---|---|---|
| 0 EXHAUSTED | `loop.py` already passes `capped=` into `_rule()` at all three exits, and holds `res.acts_tried`; the fact "the enumeration ran to its end and produced no green" is computed and then discarded into a prose `res.reason` whenever there are no greens | 0 | **derivable, not stored** |
| 1 PARTIAL | the failing COUNT. `Oracle.check()` already holds the run output in `out` and already compiles the regex that reads it (`_SUMMARY_FAIL = re.compile(r"\b(\d+) (failed\|error(?:s\|ed)?)\b")`, oracle.py) — it uses it only to catch a suite that exits 0 while reporting failures. It keeps only the first `FAILED` line and drops the count | 0 | **new, free** |
| 2 DISJOINT | the failing NODE SET, from the same string (`-q --tb=no` prints the `short test summary info` block). site(t) = sites where some single edit made failing test t pass; DISJOINT when those sets are non-empty, pairwise disjoint, and cover every baseline failure | 0 | **new, free** |
| 3 COUPLED | same data: the union of repairing sites has size 1 and covers every baseline failure | 0 | **new, free** |
| 4 CHEAP | `res.suite_runs`, `res.seconds`, `acts.candidate_cap()`, and `guard.py`'s `total_deadline`/`escalate_budget`. n singles -> n(n-1)/2 pairs x mean run seconds vs remaining budget | 0 | **derivable** |
| 5 TAUGHT | static: every observed kind k has `act_for(k) in acts.ACTS` | 0 (no suite run) | **derivable** |
| 6 CANCELING | not observable from a completed single-edit search — see finding 6 | — | **unmeasurable pre-pair** |
| 7 CAPPED | `loop.py`'s `capped` argument / `guard.py`'s deadlines; exact today | 0 | **derivable, not stored** |

Verified that `-q --no-header --tb=no` carries both the node ids and the count:

```
$ nice -n 15 .venv/bin/python -m pytest -q --no-header --tb=no -p no:cacheprovider   # in fixtures/twobug
FF                                                                       [100%]
=========================== short test summary info ============================
FAILED test_mod.py::test_count_above - assert 3 == 1
FAILED test_mod.py::test_span - assert -7 == 7
2 failed in 0.01s
```

### 4. The script, and the byte and ruling on each fixture
```
$ cd research/laws-2026-09-07/22-pair-observation-design
$ for f in single vocab twobug; do nice -n 15 .venv/bin/python observe_pair.py fixtures/$f mod.py 240; done
```
Excerpt (full provenance lines are printed by the script):

```
=== single ===   (x >= t, one failing test, one green candidate)
candidates tried  5 (enumerated 5), greens 1, 2.8s
  EXHAUSTED 0  COUPLED 1  TAUGHT 1  CHEAP 1
BYTE              56 (0b00111000)
pair_law RULING   6 = SINGLE

=== vocab ===    (bool(a or b), outside the taught vocabulary)
candidates tried  0 (enumerated 0), greens 0, 1.2s
  EXHAUSTED 1  TAUGHT 0  everything else 0
BYTE              1 (0b00000001)
pair_law RULING   3 = TEACH

=== twobug ===   (x >= t AND return lo - hi, two tests)
baseline failing  2 ['test_mod.py::test_count_above', 'test_mod.py::test_span']
candidates tried  7 (enumerated 7), greens 0, 3.7s
  EXHAUSTED 1  PARTIAL 1  DISJOINT 1  CHEAP 1  TAUGHT 1
  DISJOINT   repairing sites per test {'::test_count_above': [4], '::test_span': [10]}
BYTE              55 (0b00110111)
pair_law RULING   0 = PARTITION
```
`TEACH` on `vocab` is the same ruling `guard.py:101` writes by hand as prose. `PARTITION` on `twobug` is `docs/PAIR_LAW_PROMPT.md` incident 3, reached from a real measured search rather than from a hand-set byte. Per-candidate logs are in `search-*.json`.

### 5. The same two-bug program yields two different bytes and two different rulings, decided by pytest's `--lf` cache
`fixtures/twobug` and `fixtures/pristine` are byte-identical (`diff` reports `same` for both files) yet:

```
$ nice -n 15 .venv/bin/python observe_pair.py fixtures/twobug mod.py 240 | egrep "candidates|BYTE|RULING"
candidates tried  7 (enumerated 7), greens 0, 2.4s
BYTE              55 (0b00110111)
pair_law RULING   0 = PARTITION
$ nice -n 15 .venv/bin/python observe_pair.py fixtures/pristine mod.py 240 | egrep "candidates|BYTE|RULING"
candidates tried  5 (enumerated 5), greens 0, 1.7s
BYTE              51 (0b00110011)
pair_law RULING   2 = WIDEN
```
Stable: twobug 4/4 runs (cold and warm) at 55, pristine 3/3 at 51.

Cause, isolated with pytest's cache redirected into this directory so the shared repo-root cache is untouched:

```
$ nice -n 15 .venv/bin/python cache_probe.py fixtures/pristine
seed_full_red_run=False lastfailed_entries=1 packet.lines=[1, 2, 3, 4, 5, 6, 9]     line10_present=False
seed_full_red_run=True  lastfailed_entries=2 packet.lines=[1, 2, 3, 4, 5, 6, 9, 10] line10_present=True
```
`Oracle.failing_output()` runs `-x --tb=long` with `cache=True`. `-x` stops at the FIRST failure, so `lastfailed` records one test; `build_packet`'s coverage run is `--lf`, so it covers only that one test; so the packet names sites for only one of the two faults; so `DISJOINT` cannot be observed and the ruling is `WIDEN` instead of `PARTITION`. `twobug` differed only in having both node ids left in the shared cache from earlier runs. (The cache is the repo root's: `rootdir` resolves to `/Users/kanchetidevieswar/neo/fluidfix` because of its `pyproject.toml`, and `.pytest_cache/v/cache/lastfailed` there carries entries for many agents' fixtures, mine included — `grep -c "22-pair-observation-design" .pytest_cache/v/cache/lastfailed` -> `5`. The directory predates this session, dated `Aug 30 16:07`.)

Both rulings are correct for the situation given. `WIDEN` — "the fault is not coupled to one site; widen the search" — is the right answer when only one fault site was ever observed.

### 6. CANCELING is not observable from a completed single-edit search, so the law's central veto has no pre-pair input
The bit is defined on a pair: "green JOINTLY while each member alone leaves the suite red AND reduces nothing" (pair.py docstring; `docs/PAIR_LAW_PROMPT.md` R3). A single-edit search never evaluates a pair, so nothing it records can set it. `observe_pair.py` therefore reports `CANCELING = False` and says so in its provenance line rather than guessing.

The measurable form is a POST-condition on any pair the search finds, and every term of it comes from the same log the other bits use:

```
canceling(a, b) = green(a+b) and not green(a) and not green(b)
                  and n(a) >= baseline and n(b) >= baseline
```
`n(.)` is the failing count from finding 3, bit 1. This means the law must be consulted TWICE — once to decide whether to start a pair search, once on each green pair before it reaches the engine law. `reach.py` shows `CANCELING` unlocks no act that is otherwise unreachable (`acts reachable ONLY when CANCELING can be set: []`); what it does is grow `REFUSE` from 2 bytes to 130. It is a pure veto, exactly as R3 says, and a veto with no input is not applied at all.

### 7. `CHEAP`'s threshold is a code decision that no law owns
The comparison is `pairs x mean_seconds <= remaining_budget`. Every input exists (`res.suite_runs`, `res.seconds`, `guard.py`'s `first_deadline = t0 + budget / 3`, `escalate_budget = 600`, `acts.candidate_cap()` default 32) but the `<=` and the budget split are written in the body. Measured on `fixtures/twobug`: `n=7` singles -> `21` pairs x `0.245 s` = `5.1 s` against a 240 s budget, so `CHEAP` was true. Whether that same rule is right at Box2D scale (1,063 singles -> 564,453 pairs) is **unmeasured** here; the prompt's own figure is ~23 days.

## 4. Lanes
Reached by this work, from a real measured search: `SINGLE` (fixtures/single), `TEACH` (fixtures/vocab), `WIDEN` (fixtures/pristine), `PARTITION` (fixtures/twobug). Four of eight.

Never reached: `PAIR`, `BUDGET`, `CAPPED`, `REFUSE`.
- `PAIR` (2 of 256 bytes) needs `EXHAUSTED and PARTIAL and COUPLED and CHEAP and not DISJOINT and not CANCELING and not CAPPED` — two coupled faults on ONE site, each reducing the failing count. My fixtures had either one fault or two disjoint ones. Reaching it needs a two-fault-one-site fixture (target 24's shape) plus the failing-count measurement.
- `BUDGET` (3 bytes) needs `EXHAUSTED and not CHEAP` — a candidate space too large for the remaining budget. Unreachable on fixtures of 5-7 candidates; reachable on a real repo file (the prompt's Box2D `contact_solver.c`, 1,063 candidates).
- `CAPPED` (64 bytes) needs the deadline to fire mid-search. My budgets (240 s) were never approached (max elapsed 3.7 s). Reachable today with a small `--budget`; `loop.py` already computes the fact exactly.
- `REFUSE` (130 bytes) is 128/130 reachable only through `CANCELING`, which nothing can set (finding 6); the other 2 bytes need `EXHAUSTED and TAUGHT and CHEAP and not PARTIAL and not DISJOINT`.

Not reached, and not reachable in the body at all today: `PARTITION`, `PAIR`, `WIDEN` — see finding 2. They became reachable in this report only because `observe_pair.py` measures the failing count and failing set that the body discards.

## 5. Potential
- **One measurement unlocks three acts.** Parsing the failing count and node set from the string `Oracle.check()` already holds takes reachable acts from 5 of 8 to 8 of 8, and reachable `PARTITION` bytes from 0 to 16 and `PAIR` bytes from 0 to 2 (`reach.py`, finding 2). Cost: **zero extra suite runs** — same runs, same output, one more regex on a regex the file already compiles.
- **Worth of `PARTITION` over `PAIR` in suite runs:** on `fixtures/twobug`, 7 single-edit candidates -> 21 pairs. Linear vs quadratic at that size is 7 vs 21 runs. At Box2D scale the prompt records 1,063 vs 564,453; I did **not** re-measure that here — **unmeasured**.
- **Worth of `WIDEN` being actuated:** on the identical two-bug program, the narrow packet gives `WIDEN` (byte 51) and the wide one gives `PARTITION` (byte 55) — 5 vs 7 candidates, and the second fault's site present vs absent (finding 5). `observe_pair.py --widen` observes every signal-matching line of the defect file; I did not run it end to end, so its candidate count on a real repo file is **unmeasured**.
- **Worth of `TEACH`:** `guard.py:101` already writes this ruling as prose on the exact input (`fixtures/vocab`, byte 1) where the law rules `TEACH`. Routing it through the law would cost nothing and remove one hand-written outcome; the measured saving is **unmeasured** (it is a wording change, not a search change).
- **Worth of `CANCELING`:** it is the whole of the law's safety margin — 128 of the 130 `REFUSE` bytes. With no input for it, a pair search wired up today would run with R3 unenforced. Its value in avoided wrong repairs is **unmeasured**; the one recorded instance is the 2026-09-04 Unity `ProjectOnPlane` case, which single-edit search caught via the engine law's AMB lane, not via this bit.

## 6. Defects
1. **Observation.** `Oracle.failing_output()` uses `-x`, so `lastfailed` records one failing test, so `build_packet`'s `--lf` coverage run covers one failing test, so a two-fault program's second site is never observed and `DISJOINT` is unobservable on a cold repo. Evidence: `cache_probe.py` output in finding 5 — `seed_full_red_run=False -> packet.lines=[...,9]`, `=True -> [...,9,10]`, the only difference being one non-`-x` red run. Consequence measured: the same program rules `WIDEN` (byte 51) or `PARTITION` (byte 55) depending on cache history. **Not a ruling defect** — both rulings are correct for the byte they were given. The `-x` is deliberate (oracle.py's docstring says the cache is kept so a later `--lf` coverage run re-runs the recorded failing test); the cost of that choice is that the partition can never be seen.
2. **Observation (mine, corrected).** My first draft set `EXHAUSTED = completed and enumerated > 0 and not greens`. On `fixtures/vocab` the enumerated space is empty, so that gave `EXHAUSTED = 0`, byte 0, ruling `SINGLE` — "a single edit has not been exhausted; keep going" — for a fault with nothing left to try. An empty space is exhausted. Corrected to `completed and not greens` (comment at `observe_pair.py`, bit 0), after which the same fixture gives byte 1 and `TEACH`, which is what `guard.py` already says in prose. Recorded because it is the same failure mode the brief describes: a mismeasured bit, a correct ruling on it.
3. **Actuation.** `pair_law` is fused and never called by the body (finding 1). Nothing acts on any of its eight rulings.
4. **Not found:** no input on which `pair_law` disagreed with `tests/test_pair_law.py`'s transcribed spec. I did not re-run the 256-input equivalence (that is target 21); `reach.py` exercised all 256 inputs without an inconsistency.

## 7. Verdict
All eight PAIR observations except CANCELING are computable from data the body already holds — six of them at zero extra suite runs, since the failing COUNT and failing NODE SET sit in the very string `Oracle.check()` parses and discards — and adding that one measurement takes the law from 5 of 8 acts reachable to 8 of 8; CANCELING, the R3 veto, is undefined before a pair is tried and needs the law consulted a second time.
