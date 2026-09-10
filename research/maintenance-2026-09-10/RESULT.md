# Maintenance, full potential — measured live, 2026-09-10

**Question.** Run fluidfix the way it is sold — commit-and-forget maintenance:
watch a green suite, restore what breaks, refuse what is novel, never touch a
byte it cannot prove — and measure how much of that is real, on the released
package and on master, with every number reproducible from this directory.

**Setup.** fluidfix 0.15.0 from PyPI (the released package) and master:
`44346f7` (`b6d95a0` + the two vocabulary fixes in §1 and §3) for the first
arms, then `7233933` (+ the stale-build fix in §3; `80549e6` adds only a
test fixture) for the arms marked *fixed*. `a2f029d` (harness path),
`df1f326` (report count) and `7dc379c` (min/max spelling) were merged
after every arm had run; only the final cglm D5 re-run in §3 uses them. Every fix was found by this run and
is committed with a pinning test. Mechanical observer throughout: zero model
calls, zero tokens, by construction — nothing in this directory imports an
API client. Three arms ran on one laptop; the C arm was niced and overlapped
the others, so C wall-clock is an upper bound.

Reproduce everything: `pyrepo.py`, `catalog.py`, `rules.py`, `run_py.py`
(Python arm), `loop_props.sh` (loop properties), `run_c.sh` /
`run_c_master.sh` (cglm, first two arms), `run_box2d_master.sh` /
`run_box2d_master2.sh` (Box2D, first two runs), then the parametrised
`run_cglm.sh` / `run_box2d.sh <outdir> <budget> <label> D..` driven by
`chain2.sh` and `run_d5_kind8.sh`; the cglm copy is
`../laws-2026-09-07/37-cglm-lane-log`, the Box2D copy `36-box2d-lane-log`.
Evidence scripts: `stress_stale.py`, `replay_d1.py`, `replay_box2d_d1.py`,
`replay_box2d_d1_seq.py`, `probe_box2d_d1.py`; `classify_c.py` and
`fill_c.py` build the tables. Raw records: `results_py*.json`,
`loop_props.log`, `p2_killed.log`, `p3_watch.log`, `full_suite_*.log`,
`chain.txt`, `chain2.txt`, and one directory per arm: `c/`, `c_master/`,
`c_fixed/`, `c_fixed_900/`, `c_fixed_kind8/`, `box2d_master/`,
`box2d_master2/`, `box2d_fixed/`.

---

## 1. Python arm — the full vocabulary, scored against pristine bytes

`ledgerkit`: a six-module Python library with a 22-test pytest suite whose
boundaries are pinned with concrete values (so for each regression exactly
one one-edit program is green). For each case the driver resets to the green
base, ships the regression **as a commit**, confirms the suite is red, runs
`fluidfix guard . --commit --dictionary rules.py` exactly as the maintenance
loop would, then compares the file to the **pristine bytes** — never to "the
suite went green", because a wrong repair also goes green.

| case | class | 0.15.0 (released) | master | suite runs | reported |
|---|---|---|---|---|---|
| R01 | 0 strictness (`>=` → `>`) | byte-exact | byte-exact | 6 | 2.4 s |
| R02 | 1 literal-off-by-one (`[1:]` → `[2:]`) | byte-exact | byte-exact | 2 | 1.5 s |
| R03 | 2 swapped-return-operands (`total / units`) | **refused — miss** | byte-exact | 4 | 1.8 s |
| R04 | 3 flipped-additive (`1 + rate`) | byte-exact | byte-exact | 6 | 2.4 s |
| R05 | 8 minmax-swap (`max(0.0, x)`) | byte-exact | byte-exact | 4 | 2.0 s |
| R06 | 9 flipped-augmented-assign (`+=`) | byte-exact | byte-exact | 2 | 1.4 s |
| R07 | 10 flipped-comparison-direction (`<`) | byte-exact | byte-exact | 7 | 2.6 s |
| R08 | 11 reversed-minus-operands (`end - start`) | byte-exact | byte-exact | 6 | 2.5 s |
| R09 | 12 flipped-boolean (`True`) | byte-exact | byte-exact | 6 | 2.4 s |
| R10 | taught 4: round-lost-precision (`round(x, 2)`) | byte-exact | byte-exact | 2 | 1.4 s |
| R11 | taught 5: wrong-attribute, candidate set mined from the file | byte-exact | byte-exact | 5 | 2.1 s |
| R12 | taught 6: two lines wrong together (SpanEdit) | byte-exact | byte-exact | 4 | 1.9 s |
| R13 | same, `FLUIDFIX_MAX_LINES=1` (the cap) | repaired — **no cap in 0.15.0** | refused (correct) | — | — |
| R14 | ambiguity: two different programs both green | refused, pinning test written | same | — | — |
| R15 | a class never taught (`split(",")` → `split()`) | refused, tree untouched | same | — | — |
| R16 | green suite | nothing to do, no commit | same | — | 0.4 s |

- **Wrong repairs: 0 of 32 runs.** Every green was the pristine file, byte
  for byte. Every refusal left the working tree clean (`git status` empty)
  with the regression still committed as the teammate shipped it.
- **Released 0.15.0: 11 of 12 repair cases byte-exact; master: 12 of 12.**
  Every repair committed as `fluidfix: restore <file>:<line>`, in 2–7 suite
  runs, 1.4–2.6 s reported, under 5 s wall including the red-check.
- The ambiguity case is the shape that shipped 12 wrong repairs before
  0.15.0: `n * 2 + 1` has two one-edit greens (`n * 2 - 1` and `n * 1 + 1`)
  that agree at the suite's only input. The differential probe found the
  input where they disagree, the engine law ruled BUILT+AMB → ADD_STATE, and
  `.fluidfix/pin_me_test.py` was written instead of a guess.

### The miss, and what it was (R03)

Kind 2's signal was `^\s*return\s+.*\s(?://|[-+*])\s` and its applier used
the same alternation: floor division, minus, plus, times — **never true
division**. `return units / total` was invisible to the class. Fixed on
master (signal and applier admit `/`), pinned by
`tests/test_acts.py::test_swap_return_operands_true_division`.

### The cap (R13)

The 25-line cap (`36aca3a`, `FLUIDFIX_MAX_LINES`) is on master and in **no
released tag**. 0.15.0 has no cap, so the 2-line span landed. That is a
release-state fact, not a defect: the test measured the package correctly.

---

## 2. Maintenance-loop properties (`loop_props.sh`, `loop_props.log`)

| property | what happened |
|---|---|
| green suite | `suite green — nothing to do`, exit 0, no commit |
| **a real crash**: `kill -9` the guard while a candidate is on disk | killed 1.85 s in with `.fluidfix/inflight.json` present and `tax.py` holding a half-tried candidate (`net * (0 - rate)`). Next run: `recovered ledgerkit/tax.py: a previous run was killed mid-candidate; original bytes restored from the journal`, then repaired line 7 in 6 suite runs (2.5 s) and committed. Journal removed. |
| `--interval 4 --commit` watch mode | ticks `suite green` at :45 and :49; a regression is committed underneath it at :50; the :57 tick repairs `discounts.py:13` in 7 suite runs and commits. Nothing was re-queued — there is no queue. |

---

## 3. C arm — cglm, five real single-token defect shapes

Same five defects as the Sep 7 lane log (`37-cglm-lane-log/defects.py`:
flipped additive, index off-by-one, comparison direction, augmented assign,
min/max), `fluidfix cguard` one-shot, shipped vocabulary, `--budget 300`,
cmake rebuild per candidate, the 1,131-assertion test binary as judge.

| defect | 0.15.0 (released) | master | tree after run (before restore) |
|---|---|---|---|
| D1 vec3.h:284 flipped additive | refused, 312 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 307 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec3.h` |
| D2 ivec3.h:132 index off-by-one | refused, 311 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 306 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec3.h` |
| D3 ray.h:140 comparison direction | refused, 301 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | **repaired byte-exact**, 161 s | `1 1 include/cglm/ray.h` |
| D4 ivec2.h:318 augmented assign | refused, 313 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 302 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec2.h` |
| D5 vec2.h:653 min/max | refused, 307 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 301 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec2.h` |

**What the released package did with its budget.** `classify_c.py` diffs
every rejected candidate against the pristine line it edited:

Released 0.15.0:

```
D1:  62 rejected | {'identifier-digit': 62} | files ['vec3.h'] lines 10..37 | defect vec3.h:284 reached: False | refused
D2:  64 rejected | {'identifier-digit': 64} | files ['ivec3.h'] lines 10..34 | defect ivec3.h:132 reached: False | refused
D3:  64 rejected | {'identifier-digit': 46, 'literal': 8, 'operator': 10} | files ['ray.h'] lines 10..71 | defect ray.h:140 reached: False | refused
D4:  64 rejected | {'identifier-digit': 64} | files ['ivec2.h'] lines 10..34 | defect ivec2.h:318 reached: False | refused
D5:  64 rejected | {'identifier-digit': 64} | files ['vec2.h'] lines 10..35 | defect vec2.h:653 reached: False | refused
```

Master (after the kind-1 fix):

```
D1:  64 rejected | {'operator': 17, 'literal': 46, 'other': 1} | files ['vec3.h'] lines 100..315 | defect vec3.h:284 reached: True | refused
D2:  64 rejected | {'literal': 44, 'operator': 20} | files ['ivec3.h'] lines 80..208 | defect ivec3.h:132 reached: True | refused
D3: REPAIRED include/cglm/ray.h:140 in 56 suite runs, 155.4 s
D4:  64 rejected | {'literal': 47, 'operator': 17} | files ['ivec2.h'] lines 79..215 | defect ivec2.h:318 reached: False | refused
D5:  64 rejected | {'literal': 47, 'operator': 17} | files ['ivec2.h'] lines 79..215 | defect vec2.h:653 reached: False | refused
```

Kind 1's signal was `\d` and its applier decremented *every* digit run on
the line — including the `3` in `GLM_VEC3_ONE_INIT`. On a header whose first
forty lines are `#define GLM_VEC3_…` macros, the whole budget went to
`VEC3 → VEC2` rewrites and the defect line was never reached. The rank-1 file
**was** the defect file in every run; the file search was right and the
candidate order was wrong. Fixed on master (a digit glued to an identifier is
never a literal), pinned by
`tests/test_acts.py::test_reduce_literal_skips_digits_inside_identifiers`.

**Master, same budget.** With identifier digits no longer literals, the
candidates are real edits and the search reaches deep into each header
(`classify_c.py`: lines 100–315 of vec3.h instead of 10–37):

- **D3 repaired byte-exact** — `if (_t1 < _t2)` → `if (_t1 > _t2)`,
  ray.h:140, 56 suite runs, 155.4 s, the tree clean afterwards. The same
  defect refused on 0.15.0 and on Sep 7's 0.13.0.
- **D2 found the correct line and did not ship it.** `c_master/D2.refusal.json`
  records `greens: ["  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];"]` —
  the pristine line — with `ruling: RAISE_BUDGET`, `capped: true`. The
  budget ran out before the search could finish, so the engine law ruled
  BUILT+CAPPED → RAISE_BUDGET: a candidate that passes but has not been
  shown unique is a guess, and the guard withheld it. That is the contract
  working; whether more budget ships it is measured below.
- **D1 reached its defect line and rejected the pristine line** — the
  refusal report lists `dest[0] = a[0] + b[0];` at vec3.h:284 as tried and
  killed by "9 test(s) failed, first: glm_ray_at". Replayed on a second
  cglm copy through fluidfix's own `COracle` (`replay_d1.py`,
  `replay_d1.log`) the same sequence gives 22 / 19 / 19 / **green** / 22 /
  **green**, and the pristine binary is 0 failed in 30 of 30 runs. The
  cause is below.
- **D4, D5 never reached the defect line** in 300 s (64 candidates,
  ~4.7 s each); D5's file ranking put `ivec2.h` ahead of `vec2.h`.

### The finding that changes every C number: the suite was judging the previous candidate

`stress_stale.py` / `stress_stale.log`: write the defect, build, write the
**pristine** line immediately, judge it with fluidfix's own C oracle.
**7 of 8 cycles judged the pristine line red.** The mechanism, measured
directly (`make -q` on a source written 0.4 s after its object: exit 0):
**GNU Make 3.81 compares timestamps at whole seconds.** A C candidate cycle
is a few seconds — write, build, test, restore, write the next — so whenever
a write lands in the same second as the previous compile of that unit,
`cmake --build` skips it and the suite judges the previous candidate's
binary. A wrong candidate is red either way, so the skip is invisible; the
right one gets rejected. Box2D's D1 shows it twice: the pristine
`set.capacity = 16;` at table.c:30 was tried and rejected in both runs
(`box2d_master*/D1.refusal.json`).

This is the Sep 4 stale-binary incident (`coracle.py`, `stale_binary()`)
at the per-candidate level, where the old guard did not look. **Fixed on
master (`7233933`)**: before every build, every source touched since the
last build is moved into a later whole second than that build's end — at
most a one-second wait — so no verdict is ever cast on a binary that does
not contain the edit. Same cycles after the fix: **0 of 8 red.** Pinned by
`tests/test_c_adapter.py::test_a_candidate_written_in_the_same_second_as_its_object_is_still_built`,
with a fake `make` that compares whole seconds; the pin fails on the old
oracle and passes on the new.

Consequence for everything above: on 0.15.0 and on `44346f7`, any correct
candidate the search reached had a high chance of being judged by a stale
binary. The C arms were therefore re-run on the fixed oracle.

### cglm — master with the fix, `--budget 300`

| defect | master 44346f7 (stale oracle) | master 7233933 (fixed) | tree after run (before restore) |
|---|---|---|---|
| D1 vec3.h:284 flipped additive | refused, 307 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 309 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec3.h` |
| D2 ivec3.h:132 index off-by-one | refused, 306 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | refused, 303 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec3.h` |
| D3 ray.h:140 comparison direction | **repaired byte-exact**, 161 s | **repaired byte-exact**, 237 s | `clean` |
| D4 ivec2.h:318 augmented assign | refused, 302 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 311 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec2.h` |
| D5 vec2.h:653 min/max | refused, 301 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 310 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec2.h` |

```
D1:  52 rejected | {'operator': 12, 'literal': 40} | files ['vec3.h'] lines 100..301 | defect vec3.h:284 reached: True | refused
D2:  58 rejected | {'literal': 41, 'operator': 17} | files ['ivec3.h'] lines 80..207 | defect ivec3.h:132 reached: True | refused
D3: REPAIRED include/cglm/ray.h:140 in 56 suite runs, 229.7 s
D4:  62 rejected | {'literal': 45, 'operator': 17} | files ['ivec2.h'] lines 79..214 | defect ivec2.h:318 reached: False | refused
D5:  64 rejected | {'literal': 47, 'operator': 17} | files ['vec2.h'] lines 87..253 | defect vec2.h:653 reached: False | refused
```

With no stale verdicts left, the picture is budget and only budget:

- **D1 and D2 both find the pristine line green** (`c_fixed/D1.refusal.json`
  `greens: ["  dest[0] = a[0] + b[0];"]`, D2 likewise) inside 300 s — the
  rejection that the stale oracle produced on D1 is gone — and both are
  withheld: the search was cut short before every other candidate could be
  shown red, so the engine law ruled BUILT+CAPPED → RAISE_BUDGET rather than
  ship a candidate whose uniqueness is unproven. On the C path uniqueness
  means finishing the search; there is no differential probe for C.
- **D3 repaired byte-exact** again: 56 suite runs, 229.7 s (155.4 s before
  the fix — the extra time is the fix's whole-second waits, one per
  candidate).
- **D4 and D5 never reach their defect line** at 300 s (62 and 64
  candidates, lines 79–214 of `ivec2.h` and 87–… of `vec2.h`); D5's rank-1
  file was `vec2.h` this time.

### cglm — the budget raised as the law ruled

Every refusal that carried RAISE_BUDGET was re-run with `--budget 900` on
the fixed oracle, the operator doing what the guard said.

| defect | fixed, --budget 300 | fixed, --budget 900 | tree after run (before restore) |
|---|---|---|---|
| D1 vec3.h:284 flipped additive | refused, 309 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | refused, 905 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec3.h` |
| D2 ivec3.h:132 index off-by-one | refused, 303 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | refused, 902 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec3.h` |
| D4 ivec2.h:318 augmented assign | refused, 311 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 907 s — green found, withheld as unproven-unique (BUILT+CAPPED → RAISE_BUDGET) | `1 1 include/cglm/ivec2.h` |
| D5 vec2.h:653 min/max | refused, 310 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 908 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 include/cglm/vec2.h` |

```
D1:  64 rejected | {'operator': 17, 'literal': 47} | files ['vec3.h'] lines 100..316 | defect vec3.h:284 reached: True | refused
D2:  64 rejected | {'literal': 44, 'operator': 20} | files ['ivec3.h'] lines 80..208 | defect ivec3.h:132 reached: True | refused
D3: (no record yet)
D4:  64 rejected | {'literal': 47, 'operator': 17} | files ['ivec2.h'] lines 79..215 | defect ivec2.h:318 reached: False | refused
D5:  64 rejected | {'literal': 47, 'operator': 17} | files ['vec2.h'] lines 87..253 | defect vec2.h:653 reached: False | refused
```

- **D1 and D2 at 900 s: the pristine line is still in hand and still
  withheld.** Same ruling as at 300 s — BUILT+CAPPED → RAISE_BUDGET. On the
  C path "shown unique" means every other candidate in the packet has been
  run and rejected; a header like `vec3.h` yields hundreds of candidates at
  roughly five seconds of rebuild each, so 900 s did not finish the search
  either. Tripling the budget bought more certainty and no repair. The D1
  run's first minutes overlapped the Box2D replays above, so its candidate
  throughput is not comparable to D2's.
- **The report undercounted what 900 s tried.** Both refusals say "64
  candidate(s) were tried": the per-file rejection log keeps 64 entries
  (`loop.py`, `tried_more`), and the guard report only ever counted those.
  The true number is not recoverable from these records — roughly three
  times 64 at the 300 s run's rate. Fixed after the runs (`df1f326`: the
  summary states the total and how many are listed, the refusal file
  carries `rejected_not_listed`), pinned by
  `test_report_counts_rejections_beyond_the_64_entry_log`.
- **D4 at 900 s reaches its defect line and finds the pristine line green**
  (`c_fixed_900/D4.refusal.json`: `greens: ["  dest[0] += a[0] - b[0];"]`,
  ivec2.h:318) — which 300 s never reached — and withholds it for the same
  reason: RAISE_BUDGET, search unfinished. Three of the four re-runs now
  hold the correct line.
- **D5 at 900 s: still never reached, and it never could be.** Kind 8's
  signal is `\b(?:min|max)\(`; a word boundary cannot fall after `_`, so
  cglm's `glm_min(` matches nothing — Sep 7's finding 7, still true on
  `df1f326`. No budget reaches a line the vocabulary cannot see.
  Fixed after the arms (`7dc379c`: the signal and applier admit a
  `word_` prefix, pinned by `test_minmax_swap_sees_namespaced_spellings`)
  and D5 re-run once at 300 s on that master (`c_fixed_kind8/`): still
  refused on budget — 64 candidates reached lines 87–253 of `vec2.h`, and
  line 653 sits beyond them; the new `rejected_not_listed: 0` confirms
  exactly 64 were tried. The class can see the line now; the search has
  to walk there first, which is candidate order — Sep 7's finding 3 — and
  the ranking law's lane, not a regex.

### Box2D — master

The five single-token defects catalogued in `36-box2d-lane-log` (Sep 7: 1
repaired, 4 refused on 0.13.0), `fluidfix cguard`, `--budget 300`, the
1,300+ assertion `build/bin/test` as judge. Not run on 0.15.0 today.

**First run (`box2d_master/`): a harness fault, kept.** `run_box2d_master.sh`
wrapped each defect in a 600 s kill; D2–D5 were still building coverage
instrumentation and candidates when the wrapper killed them (`exit 124`, no
tool output), and the runner then deleted `.fluidfix/` — the crash journal
included — before the next defect. So a half-tried candidate in
`src/table.c` (`memset(..., -1, ...)`) stayed on disk under D3–D5, and those
runs measured a doubly-broken tree. `summary.txt` records every step,
including `tracked tree clean after restore: NO`. The journal the tool
writes was deleted by the script that should have let the tool read it.

**Second run (`box2d_master2/`), pre-fix oracle, stopped after D2:** wrapper
at 1800 s, journal left in place, clone restored to HEAD. D1 refused in 112 s
with the pristine line tried and judged "suite red" (the stale build); D2
refused at the budget after 611 s. D3–D5 were not run on the known-stale
oracle; the fixed arm below covers all five.

| defect | first run (harness fault) | second run (stale oracle) | tree after run (before restore) |
|---|---|---|---|
| D1 table.c:30 literal off-by-one | refused, 50 s — every candidate red (REFUTED → HARVEST_COUNTEREXAMPLE) | refused, 112 s — every candidate red (REFUTED → HARVEST_COUNTEREXAMPLE) | `1 1 src/table.c` |
| D2 math_functions.c:120 comparison direction | exit 124 (wrapper timeout) | refused, 611 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 src/math_functions.c 1 1 src/table.c` |
| D3 geometry.c:230 literal off-by-one | exit 124 (wrapper timeout) | not run | `1 1 src/geometry.c 1 1 src/table.c` |
| D4 distance.c:47 comparison direction | exit 124 (wrapper timeout) | not run | `1 1 src/distance.c 1 1 src/table.c` |
| D5 aabb.c:13 comparison direction | exit 124 (wrapper timeout) | not run | `1 1 src/aabb.c 1 1 src/table.c` |

**Fixed oracle (`box2d_fixed/`):**

| defect | master 44346f7 (stale oracle) | master 7233933 (fixed) | tree after run (before restore) |
|---|---|---|---|
| D1 table.c:30 literal off-by-one | refused, 112 s — every candidate red (REFUTED → HARVEST_COUNTEREXAMPLE) | refused, 78 s — every candidate red (REFUTED → HARVEST_COUNTEREXAMPLE) | `1 1 src/table.c` |
| D2 math_functions.c:120 comparison direction | refused, 611 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | refused, 303 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 src/math_functions.c` |
| D3 geometry.c:230 literal off-by-one | not run | refused, 303 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 src/geometry.c` |
| D4 distance.c:47 comparison direction | not run | refused, 811 s — budget, defect line not reached (CAPPED → RAISE_BUDGET) | `1 1 src/distance.c` |
| D5 aabb.c:13 comparison direction | not run | **repaired byte-exact**, 303 s | `clean` |

```
D1:  51 rejected | {'literal': 16, 'operator': 30, 'identifier-digit': 4, 'other': 1} | files ['atomic.h', 'core.c', 'ctz.h', 'main.c', 'table.c', 'table.h', 'timer.c'] lines 21..411 | defect table.c:30 reached: True | refused
D2:  64 rejected | {'literal': 40, 'operator': 24} | files ['math_functions.h'] lines 105..184 | defect math_functions.c:120 reached: False | refused
D3:  64 rejected | {'operator': 52, 'literal': 12} | files ['shape.c'] lines 22..157 | defect geometry.c:230 reached: False | refused
D4: 166 rejected | {'operator': 87, 'literal': 75, 'identifier-digit': 4} | files ['arena_allocator.c', 'atomic.h', 'bitset.c', 'body.h', 'core.c', 'id_pool.c', 'id_pool.h', 'main.c', 'recording.c', 'sensor.c', 'solver.h', 'timer.c', 'types.c'] lines 8..798 | defect distance.c:47 reached: False | refused
D5: REPAIRED src/aabb.c:13 in 9 suite runs, 20.4 s
```

What the five runs say, from their refusal reports:

- **D1 still rejects the pristine line** — `set.capacity = 16;` at
  table.c:30 tried, verdict "suite red" (a non-zero exit with no failing
  test named), the same verdict as the pre-fix run. So on Box2D the stale
  second is not the whole story. Replayed four ways on the same clone with the same
  oracle — the pristine line alone (`replay_box2d_d1.py`, 4 of 4 green),
  the arm's exact candidate order (`replay_box2d_d1_seq.py`, green), the
  full `cguard_once` flow with every build and test call logged
  (`probe_box2d_d1.py`, `probe_box2d_d1.log`: **repaired in 8 suite runs,
  18.3 s**), and finally the arm's exact command line under its wrapper
  (`box2d_d1_rerun.log`: **repaired in 8 suite runs, 17.8 s, 20 s wall**).
  The two red verdicts are not reproducible and their cause is not
  established. What both failing runs shared: each was the first guard
  invocation after a *killed* process had left `build/` behind (the
  600 s wrapper kills, then my own stop of the pre-fix arm), and a bare
  non-zero exit with no test named is what a crash in the *full* suite
  looks like — which only the correct candidate ever runs to the end,
  because every wrong one stops at the hash-set test. A corrupt artifact
  from the kill fits that shape; it is a hypothesis, not a measurement.
- **D2, D3: the wrong file first.** All 64 candidates of D2 went into
  `math_functions.h`; of D3 into `shape.c` (54 candidate files in hand);
  neither `math_functions.c:120` nor `geometry.c:230` was reached. Budget
  spent on file rank, not on the vocabulary.
- **D4: 166 candidates across 13 files in 811 s against a 300 s budget**,
  `distance.c` never ranked. The deadline is checked between candidate sets
  and between files, never inside a set; where the other 500 s went is not
  established here. **8 of the 166 candidates edited `test/main.c`** — the
  guard's own harness (`if ( argc >= 1 )` and friends), because the coverage
  tier filters candidate files with `_is_test_path`, which knew `tests/` and
  not Box2D's `test/`. The harness-silencing defence held (no green); the
  budget did not. Fixed after the runs (`a2f029d`, pinned by
  `test_the_singular_test_dir_is_a_harness_path_too`); the arms above ran
  without it.
- **D5 repaired byte-exact**: `aabb.c:13`, `d.x <= 0.0f` → `d.x >= 0.0f`,
  9 suite runs, 20.4 s of repair inside a 303 s run (the rest was
  localisation), tree clean afterwards. The same defect refused on Sep 7's
  0.13.0.


---

## 4. The full test suite on master

`full_suite_master.log`: run while both C arms were building, **220 passed,
1 failed** in 662 s — `test_multiline_logic_fix_from_one_example`, a
candidate-timeout assertion that passes 3 of 3 standalone (5 s each).

`full_suite_master_wrongpath.log`: a second run, 3 failed — all three
assertions print the *released* package's regexes and paths: `python -m
pytest tests/` from the repo root had imported the installed 0.15.0 from
site-packages, not `src/`. Fixed by `9294dc1` (`pythonpath = ["src"]` in
pyproject), so the suite tests the checkout every time.

`full_suite_master_idle.log`: master `7233933`, `src/` on the path, first
stage of the idle-machine chain: **1 failed, 221 passed in 628.36s (0:10:28)**. The one failure is
deterministic and root-caused: since `44346f7` the swap class admits `/`,
so on the fixture's only assertion for its second member (`rate(10, 0) == 0`)
the swapped program `return seconds / events` is also green, and the guard
**refused two different green programs as ambiguous** — the contract from
§1 doing its job against a fixture weaker than the vocabulary. The guard's
own words: `AMBIGUOUS: 2 candidates pass this suite and they are DIFFERENT
PROGRAMS — rate(10, 0) returns '0.0' vs '0'` — the differential probe found
the witness the suite could not see (a float zero against an int zero),
ruled BUILT+AMB → ADD_STATE, and wrote the pinning test. The fixture now
pins the direction (`rate(10, 2) == 5`, commit `80549e6`); the file passes
7 of 7.

`full_suite_final.log`, `df1f326`, idle, after the chain: **224 passed, 0 failed
in 651 s.** `full_suite_final2.log`, the final master `7dc379c` with the
min/max fix merged: **225 passed, 0 failed in 648 s.**

## 5. What this establishes, and what it does not

- **Established, Python.** On a repo whose suite pins its boundaries, the
  maintenance loop restores every shipped and taught class byte-exact in
  seconds (12 of 12 on master), refuses ambiguity and novelty with the tree
  untouched, survives a hard kill mid-write, and repairs on its own tick
  with nothing to re-queue. Zero wrong repairs in 32 runs; zero tokens.
- **Established, C.** The guard never wrote a wrong byte on cglm or Box2D
  in any of 32 runs across four arms, and every refusal left
  the tree byte-identical. With the stale-build fix, two real single-token
  defects on cglm and one on Box2D repair byte-exact from the shipped
  vocabulary inside 300 s (D3 on cglm; D5 on Box2D), and two more on cglm
  have the correct line green in hand and withheld as unproven-unique.
- **Established, and fixed — seven defects this run found in the tool and
  its tests**, each committed with a pin: identifier digits as literals
  (kind 1) and true division missing (kind 2), `44346f7`; the suite
  silently testing the installed package, `9294dc1`; the whole-second
  stale build, `7233933`; a fixture weaker than the vocabulary, `80549e6`;
  `test/` not a harness path, `a2f029d`; the report undercounting past 64,
  `df1f326`; min/max blind to `glm_min(`, `7dc379c`. None of them was a
  ruling: the laws ruled correctly on every observation they were given,
  and every one of these was an observation, a signal, or a report that
  lied to them.
- **Not established.** A hit rate on real history: `ledgerkit` is built so
  each case has one green, and real suites are weaker (cglm, 3 of 6 real
  one-token fixes invisible to its own tests, `44-author-successor-teaching`).
  The cause of Box2D D1's two unreproducible red verdicts. Where D4's
  800 s went against a 300 s budget.
- **The C-path wall now has a name, and it is not vocabulary.** Two things
  decide the rest: *file rank* (Box2D D2–D4 spent every candidate in the
  wrong file) and *the cost of proving uniqueness by exhaustion* (cglm
  D1/D2 hold the correct line and cannot ship it inside 900 s). The first
  is the SIGHT law's business and is not actuated on the C path; the second
  is the ADD_STATE lane — a differential probe for C, the way Python got one
  in 0.15.0 — so that "unique" can be shown by a witness instead of by
  running out the packet. Those are the next two lanes, not regexes.
