# 19-sight-vs-coverage

## 1. Target
On injected single-token defects in a private cglm copy, compare the SIGHT law's file ranking to the gcov coverage tier in `coracle.py`: agreement, speed, and whether combining them is a code decision today.

## 2. Method

Read (source of truth, never modified):
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/sight.py` — the law and its docstring spec.
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` lines 190-302 — the ONLY caller that consults SIGHT (`file_priority2`, Python path).
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/coracle.py` lines 341-371 (`_Coverage._ensure_build`), 395-420 (`_Coverage.lines`), 493-553 (`find_candidate_files_c`), 670-745 (`cguard_once`) — the C path.

Ran (all under `nice -n 15` + `./to.sh <secs>`, one at a time; `to.sh` is a
macOS `timeout` substitute using `perl -e 'alarm shift; exec @ARGV'`):
- `sight_vs_coverage.py defects.json results.json` -> `run.log`, `results.json`.
  18 hand-written single-token defects (`defects.json`) in 18 different cglm
  files, injected ONE at a time into the private copy at `./cglm/` (copied from
  the shared clone; restored in a `finally` after every defect; the run ends
  green — `run.log` last line `restored: build rc 0 tests rc 0`). 5 defects were
  SKIPPED because the suite stayed green (no oracle -> nothing to localise);
  13 measured. No repair was attempted; ordering only.
  Four orderings per defect, each computed on the SAME failing output:
  **BODY** (line-for-line replica of `cguard_once` 691-744), **PURECOV** (the
  gcov tier alone), **SIGHT** (the law, its 8 bits ported to C evidence, over
  the covered-file universe), **SIGHT0** (the law with the three coverage-fed
  bits forced off, over all 122 production sources).
- `followup_literal.py` -> `followup_literal.log`, `followup_literal.json`.
  4 defects re-run recording per-file bits and a SIGHT_FIX ordering in which
  LITERAL is harvested only from the `ASSERT(<expr>)` tail instead of the whole
  assert line.
- `asshipped_probe.py` -> `asshipped_probe.log`. Lets `_Coverage` configure its
  own instrumented tree the way a real `fluidfix` invocation would.
- `analyze.py` -> `analyze.log`. Recomputes every number below from the JSON.

Deviations from `guard.py`, deliberate and recorded: NAMED is resolved by
`coracle`'s own stem-affinity rule rather than `guard.py`'s `[a-z]{3,}` split
(which would turn `vec3` into `vec`, discarding the only discriminating token —
`coracle.py` 517-519 warns about exactly this); FRAMED uses `coracle._FRAME`
rather than guard's `.py`-only regex; the assert-literal regex matches any line
containing `assert`/`ASSERT` rather than guard's `^E?\s*assert` pytest anchor.

## 3. Findings

### F1 — The SIGHT law is never consulted on the C path. Combining SIGHT and coverage is not a decision anything makes today; there is no code that could make it.

```
$ grep -rn "sight" src/fluidfix/*.py | grep -v "^src/fluidfix/sight.py"
src/fluidfix/cli.py:501:    from .sight import sight as _sight          # selfcheck only
src/fluidfix/guard.py:216:  from .sight import observe_bits as _sight_bits, sight as _sight
$ grep -n "sight\|SIGHT" src/fluidfix/coracle.py
313:# single measurement drives the SIGHT law's FAILONLY lane (implicated) and
498:    the token `vec3` with `vec3.h`. Same lane the SIGHT law reads, resolved
555:        # coverage tier, so there is no evidence to rank on — the SIGHT
618:    # cost. Same insight as the SIGHT law's SCARCE lane, applied to lines.
630:            # far more than one matching 300 — the SIGHT law's SCARCE lane,
```

`coracle.py` names SIGHT five times in comments and imports it zero times. On a
C repo, file order is decided entirely by the hand-written concatenation in
`cguard_once`: frames -> NAMED-affinity score -> size -> coverage extras by
specificity -> credible-drop. SIGHT rules only on the Python path (`guard.py`).

### F2 — On cglm the gcov tier is a constant. It changed the true file's rank in 1 of 13 defects and cost 137s of the run.

`analyze.py`, sections F1-F3 (`analyze.log`):

```
=== F1  rank of the true defect file, 13 injected defects, cglm ===
  BODY   (shipped C path)  top1=10/13 top3=12/13 top5=12/13 median= 1.0 worst=42
  PURECOV(gcov tier alone)  top1= 0/13 top3= 0/13 top5= 0/13 median=38.0 worst=76
  SIGHT  (law + cov bits)  top1= 2/13 top3= 7/13 top5= 9/13 median= 3.0 worst=40
  SIGHT0 (law, no cov)  top1= 2/13 top3=10/13 top5=12/13 median= 3.0 worst=43
  PREFIX (find_candidate_files_c only, no coverage)  top1=10/13 top3=12/13
      ranks=[1, 1, 1, 1, 1, None, 1, 1, 1, 1, 1, 3, 2]
  BODY ranks  =[1, 1, 1, 1, 1, 42, 1, 1, 1, 1, 1, 3, 2]
  -> coverage tier changes the true file's rank in exactly 1/13 defects

=== F2  the gcov tier is a constant on cglm ===
  files with fail_cov == full_cov (specificity exactly 1.0): 13/13 true files
  spec_hist (files with spec>=0.9 / >=0.5 / >=0.25) per defect: {(76, 76, 76)} of {76} covered files
  spec of the true file: {1.0}

=== F3  cost ===
  gcov tier                median  10.725s  total    137.0s
  find_candidate_files_c   median   0.009s  total      0.1s
  SIGHT 8 bits             median   0.131s  total      1.9s
  suite (oracle)           median   7.418s  total     96.8s
```

The 2-to-5-file `find_candidate_files_c` prefix, computed in 9 ms, produces the
same rank for the true file as the full 10.7 s BODY pipeline in 12 of 13 cases.
The tier's single contribution across the whole run was `util_lerp`, where the
prefix does not contain the file at all and coverage put it at rank 42 of 76.

### F3 — Why the tier is a constant: the probe filter does not filter. cglm's test binary ignores its argument.

```
$ nice -n 15 ../to.sh 120 ./build/tests
1131 tests ran, 1131 passed, 0 failed
$ nice -n 15 ../to.sh 120 ./build/tests glm_mat3_det
1131 tests ran, 1131 passed, 0 failed
```

`_Coverage.lines(test_filter)` (coracle.py 411) runs `./{binary} {test_filter}`.
cglm's runner has no filtering contract, so every "probe" run is a whole-suite
run. `fail_cov` therefore equals `full_cov` exactly, and specificity is 1.0 for
all 76 covered files (F2 above). `covbuild_check.log` recorded the same thing
independently: `probe 'glm_vec3_add' coverage: 76 files in 0.39s; identical to
full? True`.

The `credible` guard in `cguard_once` (713-722) does not catch this: it tests
`len(real) < 5`, i.e. a probe that covered too LITTLE. A probe that covered
EVERYTHING passes it. `credible=True` in 13/13, so the credible-drop was applied
on coverage carrying zero information (it dropped 0-2 files; it never dropped
the true file).

### F4 — As shipped, on a clean cglm checkout, the gcov tier is not merely uninformative — it is unavailable. `_ensure_build` mirrors the build TYPE but not the flag that builds the tests.

`asshipped_probe.log` (lets `_Coverage` configure its own tree, as a real run would):

```
fast-build test_cmd: ./build/tests | build type mirrored: Release
_ensure_build ok=True in 2.2s; _test_binary() -> None
cov.lines() -> 0 files in 0.00s
  cache: CGLM_USE_TEST:BOOL=OFF
  cache: CMAKE_BUILD_TYPE:STRING=Release
  cache: CMAKE_C_FLAGS:STRING=--coverage -O0
  fast-build cache: CGLM_USE_TEST:BOOL=ON
```

`_ensure_build` (coracle.py 361-366) passes `CMAKE_BUILD_TYPE` and the coverage
flags and nothing else. cglm needs `-DCGLM_USE_TEST=ON` to emit a `tests`
target, so the instrumented tree builds no test binary, `_test_binary()` returns
None, and `lines()` returns `{}`. All the coverage numbers in F2/F3 were only
obtainable because this study's `covbuild/` was configured with tests ON
(`covbuild/CMakeCache.txt: CGLM_USE_TEST:BOOL=ON`). On a stock checkout the C
path runs on `find_candidate_files_c` alone.

### F5 — SIGHT's only POINTING bit that fires on C fires on the same two wrong files every time, because LITERAL is harvested from the absolute filesystem path.

```
=== F4  which SIGHT lanes fire on C ===
  FRAMED on a production file : 0/13
  SCARCE fired at all         : 0/13
  LITERAL fired               : 13/13, always on
        [('include/cglm/ivec2.h', 'include/cglm/vec2.h')]
  priority histogram          : [(0, 2), (1, 0), (2, 74), (3, 0) ... ]

=== F5  LITERAL is harvested from the absolute path ===
  digits >=2 in the __FILE__ path cglm's ASSERT prints: ['07', '09', '19', '2026']
  runs where all of them appear in assert_lits: 13/13
  `07` matches only the URL comment 2013/07 in vec2.h and ivec2.h:
cglm/include/cglm/vec2.h:143:  * REF: http://allenchou.net/2013/07/cross-product-of-2d-vectors/
cglm/include/cglm/ivec2.h:135: * REF: http://allenchou.net/2013/07/cross-product-of-2d-vectors/
```

The chain, every link measured: cglm's `ASSERT_EXT` macro
(`test/include/common.h` 113-124) prints `__FILE__`, which is the ABSOLUTE path;
this checkout sits under `.../laws-2026-09-07/19-sight-vs-coverage/...`; the
literal harvester takes `\d{2,}` from the assert line and so collects
`07, 09, 19, 2026` from the directory names; of the 57 distinct literals
collected across all 13 runs, exactly one — `07` — matches <= 2 files repo-wide,
and it matches a date inside a URL in a comment. LITERAL therefore promoted
`vec2.h` and `ivec2.h` to priority 0 in all 13 defects regardless of the defect.
Twice (`vec2_dot`, `ivec2_add`) the defect happened to be in one of them, which
is where SIGHT's 2/13 top-1 comes from — coincidence, not evidence.

This is a hazard of ANY checkout path containing digits (version numbers, dates,
CI job ids, `/home/user2/`), not of this directory's name specifically.

### F6 — With the path excluded from LITERAL, no POINTING bit fires at all on C and SIGHT collapses to a single priority class: all 76 files tie at priority 2.

`followup_literal.log`:

```
[vec3_add]      rank body= 1 sight= 8 sight_FIX= 6 | lits_path=19 lits_expr=2 | lit_hits_fix={} | prio {0:2, 2:74} -> {2:76}
[vec4_sub_neon] rank body= 1 sight= 9 sight_FIX= 8 | lits_path=23 lits_expr=2 | lit_hits_fix={} | prio {0:2, 2:74} -> {2:76}
[util_lerp]     rank body=42 sight=40 sight_FIX=40 | lits_path= 7 lits_expr=0 | lit_hits_fix={} | prio {0:2, 2:74} -> {2:76}
[mat4_scale_p]  rank body= 1 sight= 4 sight_FIX= 2 | lits_path= 5 lits_expr=0 | lit_hits_fix={} | prio {0:2, 2:74} -> {2:76}
```

Removing the path digits removes every discriminating literal
(`lit_hits_fix={}` in 4/4). Ranks improve slightly (8->6, 9->8, 4->2) because the
two spurious priority-0 files stop jumping the queue, but SIGHT still never
reaches BODY. With FAILONLY true for all 76 files (F2) and no POINTING bit,
`sight()` returns 2 for every candidate: **on cglm the law is a constant
function and contributes no ordering at all.** All ordering comes from the
caller's tie-break `(-named, -specificity, -n_fail, rel)`, which is the
hand-written blend, not the law.

### F7 — The degenerate coverage measurement actively DESTROYS the law's discrimination. SIGHT0 (same law, coverage bits withheld) beats SIGHT.

```
SIGHT0 bits/priority of the TRUE file per defect:
  vec3_add       prio=3  ['NAMED','TOUCHED']       rank=3/122
  vec2_dot       prio=0  ['LITERAL','NAMED','TOUCHED'] rank=1/122
  ivec3_add      prio=3  ['NAMED']                 rank=3/122
  util_lerp      prio=6  ['(none -> FLOOR)']       rank=43/122
  mat3_det       prio=3  ['NAMED','TOUCHED']       rank=3/122
  ...
SIGHT (with cov) priority of true file: [0, 2]
SIGHT0 priorities of true file:         [0, 3, 6]
```

SIGHT0 top3 = 10/13; SIGHT top3 = 7/13 (F2 table) — over a universe 122 files
wide instead of 76. The mechanism is exact: NAMED lands on mask bit 3
(priority 3) and FAILONLY on mask bit 2 (priority 2). When FAILONLY is true for
*every* file, priority 2 floods and a file with real name evidence becomes
indistinguishable from a file with none. Withhold the bogus coverage bit and the
law separates NAMED (3) from no-evidence (6) cleanly. **The law ruled correctly
on the situation it was given both times; the situation was mismeasured.**

## 4. Lanes

SIGHT emits priority 0..7. Over 13 cglm defects x 76 candidate files:

| lane | reached with coverage | reached without (SIGHT0) | why |
|---|---|---|---|
| 0 POINTING | yes, 2 files/defect — **all spurious** (F5) | yes, same 2 | only LITERAL fires, and only on path noise |
| 1 | never | never | reserved by the spec; `sight.py` docstring says priority 1 is never emitted |
| 2 FAILONLY | yes — 74-76 files/defect, i.e. everything | n/a (bit withheld) | specificity degenerate at 1.0 (F2/F3) |
| 3 NAMED | **never** | yes — true file in 11/13 | FAILONLY floods priority 2 and outranks it (F7) |
| 4 TOUCHED | never | not observed on the true file | same flooding; TOUCHED alone is rare (110 files in last 40 commits) |
| 5 SMALL | never | n/a (bit withheld) | SMALL needs coverage, and FAILONLY always co-fires |
| 6 FLOOR | never | yes — `util_lerp` | universe restricted to covered files, all FAILONLY |
| 7 UBIQUITOUS penalty | **never** | never | penalty needs specificity < 0.25; measured specificity is 1.0 for every file, every defect |

Never reached by any measurement here, and what would make each reachable:
- **FRAMED** — 0/13. Structural on C: the assertion fires in the test, so every
  frame is a `test/` file (`coracle.py` 495-499 already says so). Reachable only
  if the body resolved frames through the test's call site or a real C stack.
- **SCARCE** — 0/13. `acts.KINDS` signal regexes are Python-class shaped; none
  matched <= 2 cglm files. Reachable with C-shaped signals in KINDS.
- **UBIQUITOUS (priority 7)** and the whole 3/4/5/6 band under coverage —
  reachable only once probe coverage actually differs from suite coverage, i.e.
  once F3 is fixed.

Beyond the law: on the C path none of these lanes is reached *in production* at
all, because `cguard_once` never calls `sight()` (F1). Every lane figure above
is from this study's replica.

## 5. Potential

- **Combining SIGHT with the coverage tier is not a decision today.** It is an
  unbuilt actuation: `guard.py` consults the law, `coracle.py` does not import
  it. Wiring `cguard_once` to `sight()` as-is would, on cglm, make ranking
  strictly worse — measured: SIGHT top1 2/13 and top3 7/13 vs BODY 10/13 and
  12/13 (F2). The prerequisite is fixing the two observations, not the law.
- **Value of fixing the probe filter (F3).** On cglm: unmeasured — no per-test
  filter exists for this runner, so the counterfactual cannot be measured here.
  What IS measured is the current value of the tier: it changed the true file's
  rank in 1/13 defects for 137 s of the run (F2), and a detector costs nothing
  (`fail_cov == full_cov` => the filter did not filter).
- **Value of fixing `_ensure_build` (F4).** Unmeasured. It would move cglm from
  "tier unavailable" to "tier available but constant" (F2) unless F3 is fixed
  too; alone it buys nothing measured here.
- **Value of restricting LITERAL to the asserted expression (F5/F6).** Measured
  on 4 defects: rank 8->6, 9->8, 4->2, 40->40. It removes a false POINTING signal
  that fired in 13/13; it adds no true one on cglm.
- **Value of withholding degenerate coverage bits (F7).** Measured: top3 goes
  7/13 -> 10/13 over a 1.6x larger universe, at zero cost — the coverage bits are
  the expensive ones.
- **Speed.** The eight SIGHT bits cost a median 0.131 s; the gcov tier a median
  10.725 s; `find_candidate_files_c` a median 0.009 s (F2). SIGHT is ~82x cheaper
  than the tier it is being compared against.

## 6. Defects

Four wrong outcomes. **None is a wrong ruling.** In every case `sight()` and
`cguard_once` returned exactly what their input said; the input was wrong.

1. **OBSERVATION — LITERAL is measured off the absolute filesystem path.**
   `guard.py` 239-241 harvests `\d{2,}` from the whole assert line; ported to C,
   that line carries `__FILE__` as an absolute path. Measured (F5): 4 spurious
   literals per run, one of which (`07`) named 2 files in 13/13 runs and set the
   law's strongest tier on the wrong files every time. Evidence: `analyze.log`
   section F5, `followup_literal.log`. Fix shape: harvest from the compared
   values / `ASSERT(<expr>)` tail only, never from a path.

2. **OBSERVATION — specificity is measured from a probe that did not filter.**
   `_Coverage.lines(test_filter)` appends the filter as bare argv
   (`coracle.py` 411); cglm's runner ignores it, so `fail_cov == full_cov` and
   specificity is identically 1.0 (F2, F3). Consequence: FAILONLY fires on every
   file, UBIQUITOUS on none, and the law's 3/4/5/6/7 lanes all become
   unreachable (F7). Evidence: the two `./build/tests` runs in F3;
   `covbuild_check.log`. Fix shape: a detector — `fail_cov == full_cov` means the
   filter did not filter, so specificity carries no signal and should be
   withheld from the byte rather than reported as 1.0.

3. **OBSERVATION — the `credible` guard tests the wrong direction.**
   `cguard_once` 714-722 treats `len(real) < 5` as degenerate. A probe covering
   the ENTIRE program passes as credible: measured `credible=True` in 13/13 on
   coverage that was byte-identical to the full suite (F2). It caused no wrong
   drop here (0-2 files dropped, never the true file), but it is the guard that
   was supposed to catch defect 2 and did not.

4. **ACTUATION — the C path never consults the law it cites.** `coracle.py`
   references the SIGHT law in five comments and imports it zero times (F1).
   `cguard_once` re-implements file ordering by hand. Not a ruling error — the
   law is simply not in the circuit on C.

Not a defect: BODY's rank 42 on `util_lerp` is correct behaviour on the
observation given — `util.h` shares no token with the failing tests
(`glm_perlin_vec4`, ...), is not framed, and carries no discriminating literal, so
no lane pointed at it. SIGHT0 rules FLOOR (priority 6) on it, which is the
law correctly saying "no evidence" (F7).

## 7. Verdict

On cglm the gcov tier is a 10.7 s constant that changes the defect file's rank in 1 of 13 injections (and is entirely unavailable as shipped), while the SIGHT law is never called on the C path at all and, when replicated there, is reduced to a constant priority 2 by two mismeasured observations — a LITERAL bit harvested from the absolute checkout path and a specificity computed from a probe that never filtered — so the 9 ms `find_candidate_files_c` name-affinity prefix, not coverage and not the law, is what actually finds the file (10/13 top-1, 12/13 top-3).
