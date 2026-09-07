# 20-sight-misdirection

## 1. Target

Build a repo where the failing test NAMES a file that is not the defect; does SIGHT rank the wrong file first, and what does the body do next?

## 2. Method

Three fixtures, all built and run inside this directory; nothing outside it was written and no git state was changed. Every run was `nice -n 15 ./tmo.sh <secs> /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python <script>`, one at a time (`tmo.sh` is a `timeout(1)` substitute for this macOS box; `gtimeout` is absent).

| fixture | shape | built by |
| --- | --- | --- |
| `fixtures/named/` | pure-assertion failure. `tests/test_shell.py` fails; `pkg/shell.py` shares the token `shell` with the test module (NAMED) and is executed by that test alone (FAILONLY). The defect — `>` for `>=` in `truncate()` — lives in `pkg/types.py`, which every test executes (UBIQUITOUS). This is the click 8.5.1 incident named in `src/fluidfix/sight.py`'s docstring, reduced to 6 files. | `build_fixtures.py` |
| `fixtures/framed/` | `tests/test_api.py` -> `pkg/api.py` validates what `pkg/core.py` returned and RAISES. The traceback frames `api.py`; the defect (`a - b` for `a + b`, a taught flipped-additive) is in `core.py`, which has already returned and is in no frame. | `build_fixtures.py` |
| `work/named-literal/` | `named` plus ONE observation and nothing else: `pkg/types.py` grows `BUCKET = 95` and the failing assertion prints `b95:...`, so `95` occurs in exactly one of six source files. | `literal_variant.py` |

Fixtures carry deliberate "signal ballast" (comparisons, digits, `min`/`max`, `+`/`-`, booleans in every module) so that the shipped KINDS signals match every file and the SCARCE lane cannot fire by accident of fixture size.

Scripts kept next to this report, all re-runnable:

- `build_fixtures.py` — wipes and rebuilds `fixtures/`.
- `run_measure.py <named|framed> [--guard] [--budget N]` — records the SIGHT byte the body builds per file (by wrapping `fluidfix.sight.observe_bits` and reading the caller's `rel` local — the wrapper returns exactly what the real function returns), prints `find_candidate_files`' order, then optionally runs `guard_once` with a per-file ledger of suite runs and reasons. Each run works on a fresh copy under `work/`.
- `literal_variant.py [budget]` — builds and measures the third fixture.
- `framed_widen.py` — the frame branch, the escalation re-ask at `limit=999`, the coverage tier reached by blinding the frame mention, and a FRAMED-reachability probe.
- `framed_offered.py` — `guard_once(files=[api, core])`: what the repair costs once the defect file is merely offered.
- `func_spectrum.py` — file-level vs function-level specificity on `named`.
- `sight_r1_check.py` — exhaustive 256x256 check that widening the frame branch cannot demote a framed file.

Code read: `src/fluidfix/sight.py` (whole), `src/fluidfix/guard.py:36-310` (`GuardReport.summary`, `find_candidate_files`) and `:440-620` (`guard_once`), `src/fluidfix/engine.py`.

Housekeeping on the interrupted earlier run: three zero-content outputs (`out-named-guard_budget_{6,15,24}.txt`) held only an argparse usage error from a malformed invocation and were removed; they are superseded by `out-named-guard-b*.txt`. `func_spectrum.py` itself runs clean (exit 0) and was re-run. `framed_widen.py` existed and was extended with the two probes above. Every number below is from a run made in this session against freshly built fixtures.

## 3. Findings

### F1. On the misdirection fixture SIGHT ranks the decoy first and the defect file LAST of six

```
nice -n 15 ./tmo.sh 300 .venv/bin/python run_measure.py named --guard
```
`out-named-guard.txt`:
```
# find_candidate_files order (what guard_once's first pass walks):
   1. pkg/shell.py       byte=0x58 FAILONLY|NAMED|SMALL             priority=2
   2. pkg/__init__.py    byte=0x48 FAILONLY|SMALL                   priority=2
   3. pkg/utils.py       byte=0x40 SMALL                            priority=5
   4. pkg/core.py        byte=0x40 SMALL                            priority=5
   5. pkg/parser.py      byte=0x40 SMALL                            priority=5
   6. pkg/types.py       byte=0xc0 SMALL|UBIQUITOUS                 priority=6
# evidence: {"pointed": [], "lanes": {"FRAMED": [], "SCARCE": [], "LITERAL": []}}
```
The answer to the target's question is yes: the wrong file is opened first, and the defect file is opened sixth with the ubiquity penalty active.

### F2. The ruling is correct on the byte it was handed — this is not a ruling defect

Neither file carries a POINTING bit, so R2's gate is all-ones and the penalty is live. `sight(0x58) = 2` and `sight(0xc0) = 6` are what `docs/laws/sight.c` specifies for those inputs, and the body records its own blindness: `"pointed": []` in the evidence dict above says no POINTING lane named anything. The law ordered circumstantial evidence, which is what it was given.

### F3. With no budget the misdirection is paid for in suite runs, not in a wrong answer

Same run, `out-named-guard.txt`:
```
    {"file": "pkg/shell.py",    "suite_runs": 6, ... "repaired": false}
    {"file": "pkg/__init__.py", "suite_runs": 2, ... "repaired": false}
    {"file": "pkg/utils.py",    "suite_runs": 3, ... "repaired": false}
    {"file": "pkg/core.py",     "suite_runs": 3, ... "repaired": false}
    {"file": "pkg/parser.py",   "suite_runs": 3, ... "repaired": false}
    {"file": "pkg/types.py",    "suite_runs": 10, ... "repaired": true, "reason": "engine law: BUILT -> SHIP"}
# suite runs on WRONG files: 17, on the repaired file: 10
# guard_once(budget=None) -> status=repaired file=pkg/types.py seconds=10.0
```
17 of 27 suite runs (63%) were spent on five files that do not contain the defect. The repair itself is correct.

### F4. With `--budget` the misdirection turns the repair into a refusal, and raising the budget does not fix it

```
for b in 6 15 24 33; do nice -n 15 ./tmo.sh 300 .venv/bin/python run_measure.py named --guard --budget $b; done
```
```
# guard_once(budget=6)    -> status=refused  file=None seconds=7.9
# guard_once(budget=15)   -> status=refused  file=None seconds=7.5
# guard_once(budget=24)   -> status=refused  file=None seconds=12.7
# guard_once(budget=33)   -> status=refused  file=None seconds=14.0
# guard_once(budget=None) -> status=repaired file=pkg/types.py seconds=10.0
```
At `--budget 33` — 3.3x the 10.0 s the unbudgeted pass needs — the guard refuses after 14.0 s, leaving 19 s of the budget unspent. The mechanism is in the ledger (`out-named-guard-b33.txt`):
```
    {"file": "pkg/parser.py", "suite_runs": 1, ... "reason": "wall-clock deadline reached mid-search - remaining observations untrie"}
    {"file": "pkg/types.py",  "suite_runs": 1, ... "reason": "wall-clock deadline reached mid-search - remaining observations untrie"}
```
The first pass gets `budget / 3` (`guard.py:465`) and the five decoys consume it, so the defect file is opened with a dead clock. The escalation stage that owns the other two thirds never runs, because CAPPED is measured only from `packet.truncated` and from `len(all_files) > len(candidates)` (`guard.py:536-538`) — the packets are small and complete, and the file list does not grow, so `capped0` stays False:
```
$ .venv/bin/python -c "... decide(situation(CAPPED=c, REFUTED=r)) ..."
CAPPED=False REFUTED=True  -> HARVEST_COUNTEREXAMPLE
CAPPED=True  REFUTED=True  -> RAISE_BUDGET
```
A `repair()` that stopped on its deadline with observations untried is a capped search, and the body has that fact in `result.reason` (`loop.py:275,294`) but never turns it into the CAPPED bit. The law would have ruled RAISE_BUDGET on the true byte.

### F5. Every budgeted refusal blames the taught vocabulary, which is measurably false

```
for f in out-named-guard-b6 out-named-guard-b15 out-named-guard-b24 out-named-guard-b33; do grep -A1 "summary():" $f.txt | tail -1; done
```
```
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/shell.py, pkg/__init__.py, ...). teach it once: docs/TEACHING.md
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/shell.py, pkg/__init__.py, ...). teach it once: docs/TEACHING.md
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/shell.py, pkg/__init__.py, ...). teach it once: docs/TEACHING.md
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/shell.py, pkg/__init__.py, ...). teach it once: docs/TEACHING.md
```
The class IS in the vocabulary: the same guard with the same vocabulary repairs this defect (F3). `summary()` has two better branches for exactly this and reaches neither, because the branch selector is a substring test on the hint string:
```
src/fluidfix/guard.py:69   exhausted = "budget exhausted" in (self.hint or "")
```
and at these budgets the hint is the HARVEST_COUNTEREXAMPLE text (b6, b15, b33) or empty (b24). The comment above that line records the identical misdiagnosis on click 2026-09-02 and says blaming the vocabulary "sends the user to write a rule they already have" — the guard still does it here.

### F6. On the framed fixture the SIGHT law is never consulted at all, and the defect file is not a candidate

```
nice -n 15 ./tmo.sh 300 .venv/bin/python run_measure.py framed --guard
```
`out-framed-guard.txt`:
```
# find_candidate_files order (what guard_once's first pass walks):
   1. pkg/api.py         SIGHT NOT CONSULTED (traceback-frame branch)
# evidence: {"pointed": ["pkg/api.py"], "lanes": {"FRAMED": ["pkg/api.py"]}}
# SIGHT consulted for 0 file(s)
...
    {"file": "pkg/api.py", "suite_runs": 12, ... "rejected": 11, "repaired": false}
# guard_once(budget=None) -> status=refused file=None seconds=3.1
# candidates: ['pkg/api.py']
```
`guard.py:131-150` collects traceback-named source files and returns `ordered[:limit]` before the SIGHT import at `guard.py:216` is ever reached. This is not a low rank for the defect file — `pkg/core.py` is absent from the candidate list. 12 suite runs were spent on the wrong file and the pass refused.

### F7. Escalation cannot rescue it: the re-ask at `limit=999` returns the same single file

`out-framed-widen.txt`:
```
today (frame branch):   ['pkg/api.py']  evidence={"pointed": ["pkg/api.py"], "lanes": {"FRAMED": ["pkg/api.py"]}}
escalation (limit=999): ['pkg/api.py']  capped0 grows? False
```
`guard.py:536` widens the list by re-asking with `limit=999`, but the frame branch's `ordered` holds only files the traceback named, so the limit is not what bounds it. CAPPED does not grow and RAISE_BUDGET does not fire.

### F8. The repair was available the whole time: offering the second file repairs in 6 suite runs

```
nice -n 15 ./tmo.sh 300 .venv/bin/python framed_offered.py
```
`out-framed-offered.txt`:
```
status=repaired file=pkg/core.py seconds=5.3
lineno=33 old='return a - b ...' new='return a + b ...' suite_runs=6 reason='engine law: BUILT -> SHIP'
green after: True
```
And the coverage tier would have produced exactly that list. Blinding only the frame mention in the failing output (so the frame regex no longer matches; nothing else changed) makes the second branch run:
```
coverage tier + SIGHT:  ['pkg/api.py', 'pkg/core.py']
   pkg/api.py     measured=0x5a SCARCE|FAILONLY|NAMED|SMALL p=0   with FRAMED: 0x5b FRAMED|SCARCE|FAILONLY|NAMED|SMALL p=0
   pkg/core.py    measured=0x4a SCARCE|FAILONLY|SMALL       p=0   with FRAMED: 0x4a SCARCE|FAILONLY|SMALL             p=0
```
The framed file still comes first (the caller's affinity tie-break inside priority 0), and the defect file is second instead of absent.

### F9. Widening the frame branch cannot demote the framed file — verified exhaustively

```
nice -n 15 ./tmo.sh 60 .venv/bin/python sight_r1_check.py
```
`out-sight-r1.txt`:
```
framed bytes: 128   non-framed bytes: 128
pairs where a FRAMED file loses to a non-framed file: 0
distinct priorities a FRAMED byte can take: [0]
sight(FRAMED|UBIQUITOUS)      = 0
sight(every bit set)          = 0
sight(UBIQUITOUS alone)       = 7
priority histogram over all 256 inputs: {0: 224, 2: 8, 3: 12, 4: 6, 5: 3, 6: 2, 7: 1}
priority 1 emitted: False
```
All 128 x 128 framed/non-framed pairs: zero inversions. The early return at `guard.py:150` is therefore not protecting the frame's ranking — R1 already does that, structurally.

### F10. One added observation moves the defect file from 6th to 1st and removes every wasted suite run

```
nice -n 15 ./tmo.sh 300 .venv/bin/python literal_variant.py
```
`out-named-literal.txt`:
```
   | E       AssertionError: assert 'b95:a b c d' == 'b95:a b c'
   1. pkg/types.py       byte=0xc4 LITERAL|SMALL|UBIQUITOUS           priority=0
   2. pkg/shell.py       byte=0x58 FAILONLY|NAMED|SMALL               priority=2
   ...
# evidence: {"pointed": ["pkg/types.py"], "lanes": {"FRAMED": [], "SCARCE": [], "LITERAL": ["pkg/types.py"]}}
# suite runs on WRONG files: 0, on the repaired file: 14
# guard_once -> status=repaired file=pkg/types.py seconds=4.6
```
Same defect, same decoy, same six files. `types.py` goes 6th (p=6) -> 1st (p=0); wasted suite runs 17 -> 0; wall clock 10.0 s -> 4.6 s. Byte `0xc4` is R2 demonstrated on a live run: UBIQUITOUS is still set and is still masked.

The improvement is in the ordering, not in the budget arithmetic. At `--budget 15` the literal variant also refuses (`out-named-literal-b15.txt`), but on the right file and with an honest reason:
```
    {"file": "pkg/types.py", "suite_runs": 11, "repaired": false, "reason": "a candidate passes, but the search was cut short before it c..."}
```
which is `loop.py`'s BUILT+CAPPED -> RAISE_BUDGET text. F4's budget defect is independent of the misdirection.

### F11. FAILONLY and UBIQUITOUS are measured per FILE; at function granularity the defect region is FAILONLY, not UBIQUITOUS

```
nice -n 15 ./tmo.sh 300 .venv/bin/python func_spectrum.py
```
`out-func-spectrum.txt`:
```
file-level (what the body measures)   n_fail  n_full  specificity
  pkg/shell.py                9       9   1.00
  pkg/types.py               18      99   0.18
function-level (unmeasured by the body today)
  pkg/shell.py:render                   3       3   1.00   FAILONLY (>=0.9)
  pkg/types.py:truncate                 5       5   1.00   FAILONLY (>=0.9)
```
The failing test executes 18 of `types.py`'s 99 covered lines, and five of those are `truncate()`, which no other test executes. The proposition "specificity < 0.25" is true of the file and false of the region the failure actually reached. The penalty that put the defect file last is produced by the granularity of the observation.

### F12. FRAMED is reachable inside the branch where SIGHT runs, but only by a path that does not resolve

`out-framed-widen.txt`, last block — the frame rewritten to a non-existent `zzz/api.py`:
```
FRAMED reachability inside the SIGHT branch (frame rewritten to a non-existent zzz/api.py):
   order=['pkg/api.py', 'pkg/core.py']  evidence={"pointed": [...], "lanes": {"FRAMED": ["pkg/api.py"], "SCARCE": [...], "LITERAL": []}}
   pkg/api.py     byte=0x5b FRAMED|SCARCE|FAILONLY|NAMED|SMALL p=0
   pkg/core.py    byte=0x4a SCARCE|FAILONLY|SMALL              p=0
```
`guard.py:131-143` takes the frame branch whenever a mentioned `.py` path resolves to an existing non-test file in the root; `guard.py:218` rebuilds `framed_files` from the same regex *without* the exists/not-a-test filter. So the FRAMED bit reaches the law only when the failure names a path that does not resolve but whose basename matches a real source file. In every ordinary traceback the early return has already fired.

## 4. Lanes

SIGHT lanes and priorities this work reached, through the body's own code path:

| lane | reached | where |
| --- | --- | --- |
| FRAMED | only via F12's non-resolving path | never on any ordinary traceback: the early return at `guard.py:150` fires first, measured `SIGHT consulted for 0 file(s)` on `fixtures/framed` |
| SCARCE | yes | `framed` blinded/ghosted runs, both files |
| LITERAL | yes | `named-literal`, `pkg/types.py`, byte `0xc4` |
| FAILONLY | yes | `named` (`shell.py`, `__init__.py`), `framed` |
| NAMED | yes | `named` (`shell.py`) — the decoy lane, firing for the wrong file, as designed |
| TOUCHED | never | `recent_files` comes from `git -C <root> log`; the fixtures are not git repos, so the set is empty. Reachable on any real checkout. |
| SMALL | yes | every file in every fixture |
| UBIQUITOUS | yes | `named` (`pkg/types.py`, p=6) and masked in `named-literal` (`0xc4`, p=0) |

Priorities emitted: 0, 2, 5, 6. Never emitted here: 1 (never emitted by the law at all — measured in F9), 3, 4, 7. Priority 7 needs UBIQUITOUS with no other bit and no pointing bit; my fixture files all set SMALL.

Engine lanes reached downstream: BUILT -> SHIP (F3, F8, F10), REFUTED -> HARVEST_COUNTEREXAMPLE (F5, F6), BUILT+CAPPED -> RAISE_BUDGET as a per-file reason (F10 at budget 15). Never reached in any of these runs: the guard-level CAPPED -> RAISE_BUDGET escalation stage, because `capped0` was never measured True (F4, F7).

What would make the FRAMED lane reachable: the body already computes `framed_files` at `guard.py:218` and already has a `framed=` parameter wired into `observe_bits` at `guard.py:281`. It needs the frame branch to stop being an early return and instead seed the coverage tier — i.e. the branch at `guard.py:146-150` becomes evidence for one bit rather than a filter on the candidate list. F9 shows the framed file's position is unaffected.

## 5. Potential

- **Widening the frame branch (the missing actuation).** Measured on `fixtures/framed`: today, refused after 3.1 s and 12 suite runs on the wrong file. With the second file merely offered, `repaired` in 5.3 s and 6 suite runs (F8). Value here: one refusal converted into one repair. On real repos this is **unmeasured** — the fraction of failures whose deepest frame is a validator/assert-helper rather than the fault is not something I measured.
- **Measuring CAPPED from a deadline-truncated `repair()` (F4).** Measured: at `--budget 33` the guard leaves 19 s of 33 s unspent and refuses on a defect the unbudgeted pass repairs in 10.0 s. The escalation stage that owns two thirds of the budget is unreachable on this fixture. What the bit costs to measure: `RepairResult` already carries the reason string set at `loop.py:275,294`; `capped0` at `guard.py:536-538` would OR in "any result stopped on its deadline".
- **Function-granularity FAILONLY/UBIQUITOUS (F11).** Measured on `named`: file specificity 0.18 (penalty) vs `truncate()` specificity 1.00 (FAILONLY). Whether re-basing the two bits on the most-specific function in a file would help or hurt across many repos is **unmeasured**; the coverage data it needs is already collected by the two runs `find_candidate_files` makes.
- **The LITERAL lane's reach (F10).** Measured on this fixture: rank 6 -> 1, 17 wasted suite runs -> 0, 10.0 s -> 4.6 s. The frequency with which real failing assertions print a value occurring in <= 2 files is **unmeasured** here; `sight.py` records one click case (the literal `95` in `termui.py`).
- **Fixing the refusal wording (F5).** No suite-run saving; the value is in not sending a user to write a teaching rule they already have. **Unmeasured** as a time cost to users.

## 6. Defects

1. **Actuation.** `guard.py:131-150` returns traceback-named files and returns *before* the SIGHT law is imported or called. The law's FRAMED lane exists, is priority 0, and is R1-protected, but on an ordinary traceback the body never feeds it — measured `SIGHT consulted for 0 file(s)` (F6). Consequence: the defect file is excluded from the candidate list rather than ranked below the framed file, and the escalation re-ask at `limit=999` returns the same one file (F7). Evidence that this is the whole gap: offering the file repairs (F8), the coverage tier already produces the right list (F8), and the widening cannot demote the framed file (F9). Not a ruling defect — the law was never asked.
2. **Observation.** `capped0` (`guard.py:536-538`) is measured from `packet.truncated` and from list growth only. A `repair()` that returned on its deadline with observations untried is a capped search and is not counted, so `decide(situation(CAPPED=False, REFUTED=True))` rules HARVEST_COUNTEREXAMPLE and the escalation stage never runs. Measured: refusal at `--budget 33` after 14.0 s with 19 s unspent, on a defect the unbudgeted pass repairs in 10.0 s (F4). The engine law rules RAISE_BUDGET on the true byte.
3. **Wording** (with an observation root cause). Every budgeted refusal on `named` says "fault is outside the taught vocabulary ... teach it once", which F3 measures to be false. `summary()` has a correct branch for a search limit and a correct branch for no-pointing-evidence; the selector at `guard.py:69` is `"budget exhausted" in (self.hint or "")`, a substring test on a string that at these budgets carries the HARVEST text or nothing (F5).
4. **Observation (design).** FAILONLY and UBIQUITOUS are computed over whole-file coverage, so the file holding the defect is penalised for lines the failing test never executed. At function granularity the defect region is FAILONLY 1.00 while the file is UBIQUITOUS 0.18 (F11). This is a proposition about granularity, not a wrong ruling; I did not measure whether changing it is a net win.
5. **No ruling defect found.** In every ordering measured here, `sight()` returned what `docs/laws/sight.c` specifies for the byte it was handed, R1 held on all 128 x 128 framed pairs, and R2 held on the live byte `0xc4` (F2, F9, F10).

## 7. Verdict

SIGHT ranks the decoy first on the pure-assertion misdirection (defect file 6th of 6, p=6) and is never consulted at all on the traceback misdirection, where the body's frame branch excludes the defect file from the candidate list entirely and turns an available 6-suite-run repair into a refusal — both are body defects (one actuation, one observation) and no ruling of the law was wrong on the byte it was given.
