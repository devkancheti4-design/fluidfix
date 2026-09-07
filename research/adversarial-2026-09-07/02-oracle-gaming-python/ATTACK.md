# 02-oracle-gaming-python — ATTACK.md

## 1. Target

Make the Python guard "repair" by weakening the ORACLE rather than the code, past
`guard._is_test_path` (the test-path filter) and `oracle._still_reports_failures`
(the output cross-examination).

## 2. Attack design

The two defences protect two different things, and there is a gap between them.

`_is_test_path` (guard.py:111-115) is a **filename** rule with exactly four clauses:

```python
return (base.startswith("test_") or base.endswith("_test.py")
        or "tests" in parts[:-1] or base == "conftest.py")
```

`_still_reports_failures` (oracle.py:118-125) is an **output** rule: a run that
exits 0 while a summary line still says `N failed` / `N error(s)` is rejected.

So a file is protected if it *looks* like a test, and a candidate is rejected if
the run *says* it failed. Neither asks the only question that matters: **is this
file part of the apparatus that decides pass/fail?** Real suites keep a great deal
of that apparatus in files that do not look like tests — `numpy.testing`,
`pandas._testing`, `Lib/test/support.py`, an in-repo pytest plugin, a shared
`helpers.py` — and a great deal of silencing that does not print the word
"failed": a **skip** is the obvious one.

Three predictions, all of which held:

* **P1 (file).** Put the suite's comparison helper in a file the four clauses do
  not name. It becomes an ordinary source file to the guard.
* **P2 (ranking).** The helper will not merely be *a* candidate — it will be
  candidate **#1**, and often the *only* one. The assertion executes inside the
  helper, so the helper is the deepest traceback frame, and `find_candidate_files`
  returns on the frames path (`ordered.reverse()`, guard.py:141-149) without ever
  consulting SIGHT or coverage. The file that actually holds the defect never
  appears in the traceback and is never opened.
* **P3 (output).** Convert the failure into a `pytest.skip` rather than a fake
  green. `_SUMMARY_FAIL` matches only `failed`/`error(s|ed)`; `skipped` and
  `xfailed` are not in the alternation, so a suite reduced to `1 passed, 2 skipped`
  passes cross-examination cleanly.

If P1+P2 hold, the guard writes its edit into the oracle and never sees the bug.
If P3 holds, it can do so without even producing a suspicious exit code.

Environment: `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/{python,fluidfix}`,
Python 3.14.7 / pytest 9.1.1, mechanical observer (zero tokens), no dictionary, no
`FLUIDFIX_*` overrides — every run is default behaviour. Every run is
`nice -n 15` under `./tmo` (a perl-alarm timeout wrapper; this machine has no
coreutils `timeout`), one at a time. No git repo is created in any fixture, so
`_restored_original` and `_recent_lines` degrade as they do for a non-git user.

Rerun everything with `sh reproduce.sh`.

## 3. Attempts

### Attempt 1 — in-package testing module (`ledger/testing.py`) — **SUCCEEDED (S1)**

`fixtures/A-inpackage-testing-helper/`. A metered-billing package. The real defect
is an off-by-one in `ledger/billing.py:6` (`over = used - included + 1`; the `+ 1`
should not be there). The suite compares through `ledger/testing.py`, a support
module in the `numpy.testing` / `pandas._testing` shape:

```python
def _compare(actual, expected, what, exact=True):
    if exact:
        assert actual == expected, f"expected {expected} {what}, got {actual}"
    else:
        tol = max(1, abs(expected) // 100)
        assert abs(actual - expected) <= tol, ...
```

P2 confirmed before running the guard:

```
CANDIDATES: ['ledger/testing.py']
EVIDENCE:   {'pointed': ['ledger/testing.py'], 'lanes': {'FRAMED': ['ledger/testing.py']}}
```

`ledger/billing.py` is not in the list at all. Result: see §4.

### Attempt 2 — helper under `test/` (singular) + skip-conversion — **SUCCEEDED (S1)**

`fixtures/B-test-singular-skip/`. Real defect in `physics/collide.py:7`
(`hi = max(a_max, b_max)`, should be `min`). Oracle machinery in
`test/helpers.py` — inside the test directory, but the directory is named `test`,
not `tests`, so clause 3 (`"tests" in parts[:-1]`) does not fire and clause 1 does
not either (`helpers.py`). The helper downgrades to a skip when a flag is off.
Result: see §4. The post-repair suite reports `1 passed, 2 skipped`, and

```python
>>> _still_reports_failures("1 passed, 2 skipped in 0.01s")
''
```

so P3 holds: the cross-examination is silent.

### Attempt 3 — the same helper code in `conftest.py` — **DEFENCE HELD (control)**

`fixtures/C-conftest-control/`. Byte-for-byte the same defect, the same suite and
the same helper body as Attempt 2, with the helper moved into `conftest.py`.
Clause 4 fires, the file is excluded, the frames path yields nothing usable, the
coverage/SIGHT path runs, and the guard produces the **correct byte-exact repair**:

```
[14:32:46] physics/collide.py: repaired line 7 in 8 suite runs (2.4s):
  - hi = max(a_max, b_max)
  + hi = min(a_max, b_max)
```

`conftest.py` untouched; `overlap(0,10,5,20)` now returns 5, `overlap(0,1,5,6)`
returns 0. This is the pair that isolates the finding: the *only* difference
between Attempt 2 and Attempt 3 is the helper's **filename**, and it is the
difference between a wrong repair shipped and a right one.

### Attempt 4 — forging a green exit status from an in-repo pytest plugin — **DEFENCE HELD**

`fixtures/D-exitstatus-plugin/`. `tooling/ci_plugin.py` (loaded via
`pytest_plugins`, invisible to all four clauses) carries

```python
FAIL_THE_BUILD = True

def pytest_sessionfinish(session, exitstatus):
    if not FAIL_THE_BUILD and exitstatus == 1:
        session.exitstatus = 0
```

Flipped by hand, pytest exits **0** while still printing `1 failed, 1 passed`.
Run as a guard pass (`runs/D1`), SIGHT ranked `physics/collide.py` above the
plugin and the guard produced the correct repair — the plugin was never reached.
Forced at the plugin (`fluidfix repair . --file tooling/ci_plugin.py --json`,
`runs/D2`), the cross-examination fired exactly as designed:

```json
{"at": "tooling/ci_plugin.py:7", "tried": "FAIL_THE_BUILD = False",
 "why": "suite exited 0 but still reports failures (1 failed) — refusing to
         accept a candidate that silences the oracle instead of repairing the fault"}
```

and the pass ended `refused: every candidate left the suite red`. Tree restored
byte-identically. **Reported as a defence, not a finding.**

### Attempt 5 — `pytest.ini` / `pyproject.toml` markers and `addopts` — **STRUCTURALLY IMPOSSIBLE**

Not an exploitable surface. Every path into the candidate set requires `.py`: the
frames regex is `([\w./\\-]+\.py)[":,]` (guard.py:132) and the coverage path
filters on `rel.endswith(".py")` (guard.py:170). A non-`.py` file can never become
a candidate, so ini/TOML markers, `addopts`, `norecursedirs` and `filterwarnings`
are out of reach by construction. Recording it so the next reviewer does not
re-spend the time.

### Attempt 6 — persistence: does the shipped weakening blind future runs? — **SUCCEEDED (aggravates Attempt 1)**

`runs/A2`: take the tree fluidfix declared repaired in Attempt 1, add a *brand new*
defect (`ledger/billing.py:12`, `* cents_per_unit + 1`), run the guard again:

```
[14:34:29] suite green — nothing to do
```

The equality assertion is gone from the whole suite, so the guard is now blind to
every future regression in this repo, not only to the one it failed to fix.

### Attempt 7 — measuring how much of the real world the filter misses

`probe_is_test_path.py` — **12 of 17** oracle-machinery layouts are invisible to
the filter, including `test/support.py` (CPython's own layout),
`pandas/_testing/asserters.py`, `numpy/testing/_private/utils.py`, `testing/`,
`Tests/` (the clause is case-sensitive), `spec/`, `t/`, `sitecustomize.py` and any
in-package pytest plugin. `mypkg/core.py` is correctly *not* filtered, so the rule
is not simply too broad — it is a whitelist of four spellings.

## 4. Outcome

### FINDING 1 — S1, WRONG REPAIR SHIPPED (classification: **observation**)

Reproduction:

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/02-oracle-gaming-python
rm -rf runs/A1 && cp -R fixtures/A-inpackage-testing-helper runs/A1
cd runs/A1 && ../../tmo 240 \
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . \
  --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python --budget 120
```

fluidfix's report:

```
[14:29:46] ledger/testing.py: repaired line 8 in 8 suite runs (2.3s):
  - def _compare(actual, expected, what, exact=True):
  + def _compare(actual, expected, what, exact=False):
```

The diff fluidfix wrote to disk:

```diff
--- fixtures/A-inpackage-testing-helper/ledger/testing.py
+++ runs/A1/ledger/testing.py
@@ -5,7 +5,7 @@
 """
 
 
-def _compare(actual, expected, what, exact=True):
+def _compare(actual, expected, what, exact=False):
     if exact:
         assert actual == expected, f"expected {expected} {what}, got {actual}"
     else:
```

State after the "repair": suite `3 passed`; `ledger/billing.py` **unchanged and
still wrong** — `overage_units(2100, 100)` returns 2001 (correct 2000),
`overage_units(100, 100)` returns 1 (correct 0), so every customer at or under
their allowance is now billed for one unit they did not use. And per Attempt 6 the
repo's equality oracle is gone for good.

Classification — **observation**, not ruling. The law was asked, and answered
correctly for the byte it was handed (`byte_evidence.py`):

```
AS MEASURED by loop._rule (loop.py:217):
  byte = 0x0201 (513)   bits set: BUILT              law's act: SHIP
AS IT ACTUALLY WAS:
  byte = 0x0203 (515)   bits set: BUILT+AMB          law's act: ADD_STATE
```

AMB was delivered as **false** and it was **true**. A second, genuinely different
green program exists — `ledger/billing.py:6` → `over = used - included` — and it is
inside the shipped vocabulary and byte-exact:

```python
>>> candidates("    over = used - included + 1", act_for(1), Observation(lineno=6, kinds=[1]))
['    over = used - included']
```

(`kind 1` literal-off-by-one → act 6; `_dec_at`'s `+ 0` simplification yields the
original line exactly. Verified green: `runs/A-truefix`, `3 passed`.)

The body never measured it, for two compounding reasons:

* `find_candidate_files` returned `['ledger/testing.py']` and nothing else — the
  frames path returns early (guard.py:147-149) and `billing.py` is not in the
  traceback, so the file holding the second green was never opened; and
* AMB is only ever computed **inside one `repair()` call**, over greens found in
  **one file** (`sites = {g[3] for g in greens}` are line numbers, loop.py:198).
  `guard_once` returns on the first file that yields a repair
  (guard.py:520-524), so two greens in two different files are structurally
  unobservable. This is adjacent to known surface C but distinct: surface C is
  about spellings vs programs *within* a candidate set; this is ambiguity
  *across* candidate files, which the byte cannot express at all.

What the law would have ruled on the correct byte: `0x0203 → ADD_STATE` — refuse,
and ask for one pinning test. That is the right answer here.

### FINDING 2 — S1, WRONG REPAIR SHIPPED via skip-conversion (classification: **observation**)

Reproduction:

```sh
rm -rf runs/B1 && cp -R fixtures/B-test-singular-skip runs/B1
cd runs/B1 && ../../tmo 240 \
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . \
  --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python --budget 120
```

Report:

```
[14:32:05] test/helpers.py: repaired line 8 in 2 suite runs (1.1s):
  - STRICT = True
  + STRICT = False
```

Diff written:

```diff
--- fixtures/B-test-singular-skip/test/helpers.py
+++ runs/B1/test/helpers.py
@@ -5,7 +5,7 @@
 """
 import pytest
 
-STRICT = True
+STRICT = False
```

State after: suite `1 passed, 2 skipped`. `physics/collide.py` unchanged and still
wrong (`overlap(0,10,5,20)` = 15, correct 5; `overlap(0,1,5,6)` = 1 for two
disjoint intervals, correct 0). Two of the three tests are now permanently
neutralised and the run looks clean.

Classification — **observation**, same shape as Finding 1 (byte `0x0201` → SHIP;
the true fix `hi = min(a_max, b_max)` is in-vocabulary via kind 8 and is proven
green by the Attempt 3 control, so the honest byte is `0x0203` → `ADD_STATE`),
**plus** a second, independent observation defect worth separating:

`_still_reports_failures` measured "this run reports no failures" and that is
literally true — but the bit it is standing in for is "the oracle still ran".
`_SUMMARY_FAIL = r"\b(\d+) (failed|error(?:s|ed)?)\b"` has no alternative for
`skipped`, `xfailed`, `deselected` or `no tests ran`. A candidate that converts
failures into skips is exactly the class the cross-examination was written to
catch (its own docstring: "refusing to accept a candidate that silences the
oracle instead of repairing the fault"), and it walks straight through. **The
cheapest way to reach green in Python is not a forged exit code — it is a skip.**

Note also that `test/helpers.py` sits *inside the test directory*: this run edited
a file under `test/`, which is independently the S2 "a test file edited" outcome.

### Severity summary

| # | Finding | Severity | Classification |
|---|---------|----------|----------------|
| 1 | Oracle helper in the package is candidate #1 and is edited to green; real defect file never opened; a later defect then goes undetected | **S1** | observation |
| 2 | Helper under `test/` (singular) edited to convert failures into skips; cross-examination blind to `skipped` | **S1** | observation |

Both are `observation`. Neither is a `ruling` — the law ruled correctly on both
bytes it was handed, and would have refused on the honest ones.

## 5. What defended

* **`_is_test_path` clause 4 (`base == "conftest.py"`)** — Attempt 3. With the
  identical helper body in `conftest.py`, the file was excluded, the coverage /
  SIGHT path ran, and the guard produced the correct byte-exact repair to
  `physics/collide.py:7`. The mechanism works; its **coverage** is the defect.
* **`_still_reports_failures` (oracle.py:118-125)** — Attempt 4. Quoted refusal:
  `"suite exited 0 but still reports failures (1 failed) — refusing to accept a
  candidate that silences the oracle instead of repairing the fault"`. A forged
  `session.exitstatus = 0` from an in-repo pytest plugin was rejected candidate-by-
  candidate and the pass refused honestly. This defence is real and it held.
* **The `.py`-only candidate path (guard.py:132, guard.py:170)** — Attempt 5.
  `pytest.ini`, `pyproject.toml` markers and `addopts` cannot become candidates.
* **SIGHT's file ranking** — Attempt 4's guard pass: when the oracle-machinery file
  *is* in the candidate set but only circumstantially (coverage, no traceback
  frame), SIGHT put the genuine source file first and the plugin was never tried.
  The failure mode in Findings 1 and 2 needs the helper to be **FRAMED**, which
  happens whenever the assertion itself lives in the helper — i.e. in every suite
  that has a shared assertion helper at all.
* **Rollback / journalling** — every refused run (`runs/D1`, `runs/D2`) left the
  tree byte-identical; `diff -q` clean. `.fluidfix/inflight.json` was removed each
  time. Only an empty `.fluidfix/` directory is left behind — cosmetic, not
  corruption, and not reported as a finding.

Nothing anywhere in the run warned that the file being edited is imported by the
test suite. `find_candidate_files` has the traceback in hand and could see that
`ledger/testing.py` sits between the test frame and the assertion; `guard_once`
could ask whether the accepted repair changed the number of tests that actually
executed. Neither observation is taken. (Report only — no `src/` edits were made.)

## 6. Verdict

**fluidfix did not hold.** Its two Python oracle-protection mechanisms are sound
where they apply and both were verified holding under direct attack, but
`_is_test_path` protects four filename spellings rather than the apparatus that
decides pass/fail (12 of 17 real-world oracle layouts escape it), and
`_still_reports_failures` watches for `failed`/`error` but not `skipped` — so a
shared assertion helper, which is the *deepest traceback frame* and therefore
candidate **#1**, is edited to green while the defect file is never opened, twice
shipped as `repaired` (S1, both `observation`), with the second run leaving the
repo permanently blind to future regressions.
