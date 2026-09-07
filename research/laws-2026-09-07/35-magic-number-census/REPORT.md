# 35-magic-number-census

## 1. Target

Every hardcoded constant in the fluidfix **body** — numeric threshold or fixed
name list alike — that changes a repair OUTCOME; for each, its line number,
the outcome it changes, which law should own it, and as which bit.

## 2. Method

Read in full: `src/fluidfix/guard.py`, `loop.py`, `acts.py`, `oracle.py`,
`localize.py`, `sight.py`, `engine.py`, `rank.py`; `coracle.py` lines 80-310
and 560-771; `pair.py` 1-70. Body = the modules that MEASURE and ACTUATE
(`loop, guard, acts, oracle, coracle, localize, observers, hotspots,
javaoracle, cli`); the six law kernels are excluded — their constants are the
authored word and not the body's to own.

Scripts written (all in this directory; all pure-function or read-only —
nothing was built, no suite was run, no repo was mutated):

| script | what it does | output |
|---|---|---|
| `nt.sh` | `nice -n 15` + perl-`alarm` timeout wrapper (this machine has no coreutils `timeout`) | — |
| `census.py` | AST-walks the body, emits every numeric literal and every hardcoded string tuple/list/set with file:line | `nums.txt` (500 lines), `strs.txt` (50) |
| `verify_six.py` | verifies the six constants the coordinator named, and the outcome each changes | `verify_six.out` |
| `testpath_probe.py` | `guard._is_test_path` against 17 real-world oracle layouts | `testpath_probe.out` |
| `testpath_realrepos.py` | the same function against the **actual** Box2D and cglm test trees | `testpath_realrepos.out` |
| `divergence.py` | replays the arithmetic of the constants whose stated intent and measured behaviour differ | `divergence.out` |
| `cap_bites.py` | does `acts._CAP_DEFAULT=32` truncate real candidate sets? | `cap_bites.out` |

Wrapper verified before use:

```
$ ./nt.sh 5 /bin/sh -c 'sleep 30'; echo "rc=$?"
TIMEOUT after 5 s
rc=124
```

## 3. Findings

### F1 — The six named constants, verified

`./nt.sh 120 .venv/bin/python verify_six.py` (full output: `verify_six.out`).
All six exist where the coordinator said, and each changes an outcome:

| # | constant | line | outcome it changes |
|---|---|---|---|
| C1 | coverage credibility floor `len(real) < 5` | `coracle.py:715` | gates `credible`, which gates the candidate-set DROP at 741-744 |
| C2 | default confirmation count `1` | `loop.py:104` | `0` switches OFF the engine law's HIDDEN lane entirely (`loop.py:357`) |
| C3 | `file_share` escalation cap `/2` | `guard.py:591-592` | one file's slice of the escalation clock |
| C4 | harvest cap `64` per file | `loop.py:346, 407` | size of HARVEST_COUNTEREXAMPLE's payload |
| C5 | SIGHT `SMALL` bound `80` | `guard.py:287` | file search order (measured below) |
| C6 | test-path whitelist, four spellings | `guard.py:111-115` | whether a file is a repair candidate at all |

Excerpts:

```
C1  715: if len(real) < 5:
    743: if len(touched) >= 3:   <- a SECOND, undocumented floor
      len(real)= 4  credible=False -> drop-non-executed = False
      len(real)= 5  credible=True  -> drop-non-executed = True

C2  104: return max(0, int(os.environ.get("FLUIDFIX_CONFIRM", "1")))
      FLUIDFIX_CONFIRM=None   -> _confirm_runs()=1
      FLUIDFIX_CONFIRM=0      -> _confirm_runs()=0
      FLUIDFIX_CONFIRM=junk   -> _confirm_runs()=1

C5  287: small=0 < n_fail < 80,
      n_fail=  79  SMALL=True  byte= 64  sight()=5
      n_fail=  80  SMALL=False byte=  0  sight()=6  <-- ruling changes here
      n_fail=  79  FRAMED=True byte= 65  sight()=0   (R1: pointing dominates)
```

C5 is the cleanest demonstration of the structural point: **the law owns the
bit, the body owns the threshold.** `sight()` reads a boolean; `80` is the
only thing that decides which boolean. And under a POINTING bit the number is
algebraically inert (R1), so it matters exactly in the situation the guard's
own third-refusal-cause text calls arbitrary (`guard.py:82-91`).

### F2 — The test-path whitelist: 12 of 17 layouts escape (reproduced), and it is the *harness* files that escape on the real repos

`./nt.sh 60 .venv/bin/python testpath_probe.py` -> `testpath_probe.out`:

```
test/foo.py                  True            False         ESCAPES     dir named `test` (singular)
testing/foo.py               True            False         ESCAPES     django/numpy `testing`
unit_tests/runner.py         True            False         ESCAPES     coracle.py:125 knows this one
check/main.c                 True            False         ESCAPES     coracle.py:125 knows this one
test/joint_test.c            True            False         ESCAPES     Box2D-shaped C test
Tests/FooTests.py            True            False         ESCAPES     capitalised `Tests` dir
...
12 of 17 layouts are real test files that ESCAPE the whitelist
```

Independently reproduces the red team's 12/17. Two of the escaping spellings
(`unit_tests/`, `check/`) are ones **fluidfix itself knows about elsewhere**:
`coracle.py:125` searches `("tests", "test", "unit_tests", "run_tests",
"check")` for the test binary. The knowledge exists in the codebase and the
filter does not read it.

The stronger measurement is on the two repos this project actually benchmarks
on. `./nt.sh 120 .venv/bin/python testpath_realrepos.py` ->
`testpath_realrepos.out`:

```
box2d: oracle source files under its test tree: 18
  recognised by _is_test_path: 17
  ESCAPE (fluidfix may edit its own oracle): 1
    test/main.c

cglm: oracle source files under its test tree: 42
  recognised by _is_test_path: 38
  ESCAPE (fluidfix may edit its own oracle): 4
    test/runner.c
    test/tests.h
    test/include/common.h
    test/src/tests.c
```

The escapees are not incidental files — they are the **runners**. And
`box2d/test/main.c` holds precisely the shape of the recorded C-adapter
incident:

```
$ grep -n "return" box2d/test/main.c
121:		return 1;
125:	return 0;
```

`oracle.py:97-105` and `coracle.py:272-281` both record that incident in
words: *"the guard changed the harness's failing `return 1` to `return 0`, left
the defect untouched, and declared success"*. Kind 1 (literal-off-by-one,
signal `\d`) applied by `_reduce_literal` turns `return 1;` into `return 0;` —
the cheapest path to green. `_is_test_path` is named in `oracle.py:102` as the
first defence, and on Box2D it does not cover the one file where that edit
lands.

**Neither overstated nor understated:** a second defence exists and is real —
`coracle.check()` (`coracle.py:283-291`) cross-examines a zero exit code
against `_fail_names(out)` and refuses a suite that still *says* it failed.
That defence, not the whitelist, is what has been holding. Whether it holds on
`box2d/test/main.c` specifically is **unmeasured** — I did not build Box2D
(the brief allows real-repo runs only if the target says so; mine does not).

`_is_test_path` is pinned by **no test at all**:

```
$ grep -rn "_is_test_path" tests/
tests/test_c_adapter.py:209:    `_is_test_path` to keep test files out of the candidate set, but a
```

— a comment inside a test of the *other* defence.

### F3 — `guard.py:591-592`: the anti-starvation cap is inert for the second half of the escalation clock, in the no-`--budget` path only

`./nt.sh 120 .venv/bin/python divergence.py` -> `divergence.out`. The comment at
`guard.py:588-590` states the intent: *"one file gets at most half the
escalation budget (adversarial review, 2026-08-31 — depth-first starvation)"*.
Replaying lines 591-597 exactly:

```
  no --budget  (total_deadline is None; file_share = escalate_budget/2)
  t (s into escalation)    clock left  file_share    ACTUAL slice
  0                               600         300             300
  300                             300         300             300   <- NOT half of what is left
  450                             150         300             150   <- NOT half of what is left
  599                               1         300               1   <- NOT half of what is left
  with --budget (total_deadline set; file_share = (deadline-now)/2)
  300                             300         150             150
  450                             150          75              75
```

In `--budget` mode the share is `(deadline - now)/2` and the invariant holds
at every instant. Without `--budget` the share is the **constant**
`escalate_budget/2`, and `min(deadline, now + 300)` collapses to `deadline`
once fewer than 300 s remain. So from the halfway point onward the *next* file
takes the entire remainder and every file after it gets nothing — which is the
starvation the constant was introduced to prevent. `escalate_budget` defaults
to 600 (`guard.py:443`), so this is the default path, not an edge case.

`file_share` is pinned by no test (`grep -rn file_share tests/` -> 0 hits).

### F4 — `guard_once`'s docstring contradicts its own code on the budget split

```
$ sed -n '452,468p' src/fluidfix/guard.py
    `budget` (optional) caps the ENTIRE pass: the first pass may spend at
    most half of it — ...
    # first pass gets a THIRD of the budget; escalation gets the rest.
    # Measured (v0.7 span bench round 2): a half/half split let blind
    # first-pass grinding starve the full-sight escalation stage that
    # actually repairs — termui's round-1 win regressed to a refusal.
    first_deadline = t0 + budget / 3 if budget else None
```

The docstring says *half*; the code and the inline comment two lines below say
*a third*. The number was changed for a measured reason and the docstring was
not. `budget / 3` is pinned by no test.

### F5 — The candidate cap (`acts.py:376`, 32) is invisible to the engine law, but does not bite on the shipped vocabulary

`grep -n "CAPPED=" src/fluidfix/*.py` returns exactly three sites:
`guard.py:539`, `loop.py:219`, `pair.py:157`. None is fed by
`candidate_cap()`. `acts.py:406` slices the candidate list and nothing
upstream learns that the slice dropped anything, so a truncated candidate set
is an **UNCAPPED** situation as far as `decide()` is concerned — while a
truncated *packet* or *file list* is correctly CAPPED (`guard.py:508, 538`).

How much that costs today, measured (`cap_bites.out`):

```
candidate_cap() = 32  (acts.py:376 _CAP_DEFAULT)
lines scanned: 23194
candidate sets a cap of 32 truncates: 0
  none on these two trees at the default cap.
```

So on Box2D `src/` and cglm `include/`, with the shipped kinds, the cap never
bites. The gap is real but latent; `acts.py:370-375` records the situation
where it does bite (taught name-shaped classes on SQLAlchemy: the exact fix
generated but at ranks 42..10,563).

### F6 — The full census

**Group A — a threshold behind a law bit** (the law owns the bit, the body
owns the number). "In spec" = the law module's own docstring states the number.

| line | constant | outcome it changes | law / bit | in spec? |
|---|---|---|---|---|
| `guard.py:254` | `0 < len(hits) <= 2` | LITERAL fires | SIGHT bit 2 LITERAL | yes (`sight.py:17`) |
| `guard.py:272` | `0 < len(hits) <= 2` | SCARCE fires | SIGHT bit 1 SCARCE | yes (`sight.py:16`) |
| `guard.py:284` | `specificity >= 0.9` | FAILONLY fires | SIGHT bit 3 FAILONLY | yes (`sight.py:18`) |
| `guard.py:287` | `0 < n_fail < 80` | SMALL fires | SIGHT bit 6 SMALL | yes (`sight.py:21`) |
| `guard.py:288` | `specificity < 0.25` | UBIQUITOUS penalty | SIGHT bit 7 UBIQUITOUS | yes (`sight.py:22`) |
| `guard.py:224` | `git log -40` | TOUCHED fires | SIGHT bit 5 TOUCHED | yes (`sight.py:20`) |
| `guard.py:310` | `depth: int = 40` | RECENT fires | RANK bit 4 RECENT | **no** — `rank.py:18` says only "the most recent commits" |
| `guard.py:403` | `0 < n < 8` | CHEAP fires | RANK bit 5 CHEAP | yes (`rank.py:19`) |
| `guard.py:402` | `(obs.kinds or [])[:2]` | CHEAP counted from the first 2 kinds only | RANK bit 5 CHEAP | **no** |
| `guard.py:412` | `shapes[...] >= 8` | DENSE fires | RANK bit 6 DENSE | **no** — `rank.py:20` names no number |
| `localize.py:89` | `max_lines=110` | `packet.truncated` | ENGINE bit 5 CAPPED | no |
| `localize.py:164` | `max_lines - 30` | signal-filter trigger -> `filtered` -> CAPPED | ENGINE bit 5 CAPPED | no |
| `localize.py:124` | frame window `+/-12` | which lines reach the observer | SIGHT/RANK bit 0 FRAMED/FRAME | no |
| `localize.py:82` | span cap `<= 40` | statement expansion of covered lines | ENGINE bit 5 CAPPED (indirect) | no |
| `guard.py:578, 582` | `990`, `10**9` | the escalation sight ladder | ENGINE act RAISE_BUDGET | no |
| `coracle.py:565, 584, 651` | `110`, `+/-12`, `-30` | same, C side | ENGINE bit 5 CAPPED | no |
| `coracle.py:644-645` | rarity fallback `10**6`, `[:max_lines]` | which C lines survive to the observer | ENGINE bit 5 CAPPED | no |
| `loop.py:104` | `FLUIDFIX_CONFIRM` default `1` | whether HIDDEN can ever be measured | ENGINE bit 4 HIDDEN | partly (`loop.py:94-106`) |
| `loop.py:346, 407` | `< 64` | harvest payload per file | ENGINE act 6 HARVEST_COUNTEREXAMPLE | no |
| `guard.py:719` | `attempts[:200]` | harvest payload per report | ENGINE act 6 | no |
| `loop.py:348-349, 409` | `[:200]`, `[:400]` | harvest entry truncation | ENGINE act 6 | no |
| `acts.py:376` | `_CAP_DEFAULT = 32` | candidate-set truncation | **ENGINE bit 5 CAPPED — never wired** (F5) | no |

**Group B — gates an outcome with no law bit at all.** These are the ones the
standing principle would call *code deciding*.

| line | constant | outcome it changes | which law should own it, as which bit |
|---|---|---|---|
| `coracle.py:715` | `len(real) < 5` | whether non-executed files are dropped from the candidate set | ENGINE bit 2 **UNREAD** -> ADD_MATERIAL. Degenerate coverage *is* "a needed tool reads nothing"; today the body silently changes strategy instead of asking. |
| `coracle.py:743` | `len(touched) >= 3` | second gate on the same drop | same bit; undocumented anywhere |
| `coracle.py:710` | `[:4]` failing-test probes | how much coverage evidence exists | ENGINE bit 5 CAPPED (evidence budget) |
| `coracle.py:246, 265` | `[:40]` failing-test names | same | ENGINE bit 5 CAPPED |
| `guard.py:119` | `limit: int = 3` | how many FRAMED files pass 0 tries | SIGHT is consulted for *order*, never for *depth*; the cut-off has no owner. Feeds ENGINE CAPPED only indirectly at `guard.py:538`. |
| `guard.py:302` | `max(limit, 8)` | how many coverage-ranked files pass 0 tries | same — and note pass 0 takes **3** framed files but **8** coverage-ranked ones, an asymmetry with no stated reason |
| `guard.py:468` | `budget / 3` | first-pass/escalation split | ENGINE bit 5 CAPPED -> RAISE_BUDGET. Contradicted by its own docstring (F4). |
| `guard.py:443` | `escalate_budget = 600` | when CAPPED stops being retried | ENGINE bit 5 CAPPED |
| `guard.py:591-592` | `/2` file_share | per-file starvation cap | no law bit; broken in the default path (F3) |
| `oracle.py:120` | `timeout=300` | a candidate that overruns returns `(1, "TIMEOUT")` — a **rejection**. A too-short timeout manufactures REFUTED. | ENGINE bit 6 REFUTED is being set by the clock, not by the suite. The honest bit is CAPPED. |
| `oracle.py:120` | `per_test_timeout=60` | same, per test | same |
| `coracle.py:102` | `timeout=600`, `jobs=8` | same, C side | same |
| `oracle.py:111` | `splitlines()[-25:]` | how far back the "suite exited 0 but still reports failures" defence looks | this is the *second* defence's own magic number (F2) |
| `coracle.py:172` | staleness slack `- 1` second | whether a stale binary is declared | ENGINE bit 2 UNREAD (the oracle is not reading the current source) |
| `localize.py:68-69` | `800`, `[:300]`, `[-450:]` | how much failure text the observer sees | ENGINE bit 5 CAPPED |
| `observers.py:92` | `max_tokens = 16000` | LLM observer output budget | ENGINE bit 5 CAPPED |

**Group C — fixed name lists that decide an outcome.** Same class of constant,
different type.

| line | list | outcome it changes |
|---|---|---|
| `guard.py:111-115` | 4 test-path spellings | whether fluidfix may edit its own oracle (F2) |
| `guard.py:307` | `("test", "tests")` token stoplist | RANK bit 2 NAMED |
| `oracle.py:57-61` | `_EXIT_MEANING = {3, 4, 5}` | HarnessError vs a red suite — i.e. "no verdict possible" vs "repairable" |
| `oracle.py:215, 236` | `("FAILED", "ERROR")` | the `why` string harvested per rejection |
| `oracle.py:106` | `_SUMMARY_FAIL` regex | the silenced-suite defence |
| `coracle.py:88` | `_SRC_EXT`, 8 extensions | which files can be candidates at all (C) |
| `coracle.py:125, 389` | 5 / 4 test-binary names | which binary *is* the oracle |
| `coracle.py:600` | 8 comment/preproc prefixes | which C lines can be anchors |
| `coracle.py:75-87` | `_FAILTEST` 5 runner shapes | `_fail_names` -> the silenced-suite defence AND the coverage probe set |
| `localize.py:65` | 5 line prefixes | what the observer sees of the failure |
| `javaoracle.py:121` | `(".git","target","node_modules")` | which Java files are candidates |
| `javaoracle.py:170` | 5 prefixes | which Java lines are anchors |
| `acts.py:74-114` | `KINDS` 12 signal regexes | which lines are SIGNALED (RANK bit 3) and SCARCE (SIGHT bit 1) |

### F7 — Not one census constant is pinned by a test

```
$ for pat in _is_test_path file_share tried_more credible 0.25 "budget / 3" \
      _CAP_DEFAULT candidate_cap "dense=" "cheap="; do
    echo "$pat -> $(grep -rn -- "$pat" tests/ | wc -l) test hits"; done
_is_test_path -> 1 test hits      (a comment, tests/test_c_adapter.py:209)
file_share -> 0 ; tried_more -> 0 ; credible -> 0 ; 0.25 -> 0
budget / 3 -> 0 ; _CAP_DEFAULT -> 0 ; candidate_cap -> 0
dense= -> 0 ; cheap= -> 0
```

The one genuine exception is `FLUIDFIX_CONFIRM`
(`tests/test_c_adapter.py:382-398`), which pins the default at 1 and the
parse behaviour. Every law kernel is pinned exhaustively over all 256 inputs;
every threshold that *feeds* those kernels is pinned by nothing.

### F8 — The C guard never consults the engine law

```
$ grep -rn "situation(" src/fluidfix/{loop,guard,acts,coracle,oracle,cli}.py
src/fluidfix/loop.py:217, 391
src/fluidfix/guard.py:491, 539, 612, 618
src/fluidfix/cli.py:474
```

`cguard_once` (`coracle.py:670-771`) contains none. The C path has no
CAPPED->RAISE_BUDGET escalation, no UNREAD->ADD_MATERIAL hint and no
REFUTED->HARVEST hint; it iterates its candidate list once and refuses. It
reaches the law only indirectly, through `loop.repair()`.

## 4. Lanes

**SIGHT law.** Reached and exercised by measurement: FRAMED, SCARCE, LITERAL,
FAILONLY, NAMED, TOUCHED, SMALL, UBIQUITOUS — all eight have a body-side
measurement (`guard.py:281-289`), and `divergence.out` D2 shows each moves a
file by exactly one priority class while none can beat a POINTING bit (R1
holds as authored). Never reached: nothing. The law is fully wired; only its
*thresholds* are unowned.

**RANK law.** Reached: FRAME, NAMED, SIGNALED, RECENT, CHEAP, DENSE, RETRIED.
**Never reached: FAILONLY (bit 1)** — `rank_observations` (`guard.py:406-414`)
passes no `failonly=` argument at all, and `guard.py:352-354` says so
explicitly. It would need line-level coverage of the failing *and* passing
sets. RETRIED's veto is reachable but `retried` is only ever passed as `None`
from `guard_once` (`guard.py:511-513, 585-587`), so the veto is **unreachable
in the guard today** — it is reachable only via a direct
`rank_observations(..., retried=...)` call.

**ENGINE law.** Reached from the body: BUILT, AMB, CAPPED, UNREAD, REFUTED,
HIDDEN (six of eight). Never reached: NOTWIN, SELF — as the docstring says.
CAPPED is reached from three sources (packet truncation, file-list truncation,
wall clock) but **not** from candidate-set truncation (F5).

**PAIR law.** Not reached at all — fused, not actuated; no `pair.py` call
exists in the body.

## 5. Potential

- **Wiring `acts.candidate_cap()` truncation into ENGINE CAPPED** would make
  RAISE_BUDGET reachable for the case `acts.py:370-375` already measured (the
  taught SQLAlchemy classes whose exact fix sat at ranks 42..10,563). Cost
  today on the shipped vocabulary: **0 of 23,194 real C source lines produce a
  set larger than 32** (`cap_bites.out`), so the immediate value is zero and
  the value on taught name-shaped classes is **unmeasured** here.
- **Fixing `guard.py:591-592`** so the no-`--budget` path uses
  `(deadline - now)/2`: restores the stated invariant for every file after the
  escalation halfway point. How many repairs that would recover is
  **unmeasured** — it needs real-repo escalation runs, which my target does
  not authorise.
- **Promoting `coracle.py:715`'s floor to an ENGINE UNREAD observation**: the
  law would rule ADD_MATERIAL and the guard would tell the user their gcov
  probe is degenerate, instead of silently switching to whole-suite coverage.
  Frequency of the degenerate branch on real repos: **unmeasured**.
- **Widening `_is_test_path`** to the names `coracle.py:125` already lists
  (`test`, `unit_tests`, `run_tests`, `check`), to case-insensitive matching,
  and to non-`.py` suffixes: measured effect is 1 of 18 Box2D and 4 of 42 cglm
  oracle files stop being candidates (F2). Whether any of those five would
  ever have been *reached* by the ranking, and whether `coracle.check()`'s
  cross-examination would have caught the edit, is **unmeasured**.

## 6. Defects

1. **`guard.py:591-592` — actuation.** The comment states an invariant ("one
   file gets at most half the escalation budget") that the code does not hold
   in the default no-`--budget` path (F3, `divergence.out` D1). No law ruled
   wrongly: no law was asked. The body is actuating a starvation guard that
   switches itself off halfway through the clock.
2. **`guard.py:452-453` vs `guard.py:468` — wording.** The docstring says the
   first pass may spend "at most half" the budget; the code spends a third and
   the adjacent comment says a third (F4). The number was changed for a
   measured reason; the docstring was not updated.
3. **`guard.py:111-115` — observation.** The whitelist is a four-item
   approximation standing in for the measurement "is this file part of the
   project's own oracle?". 12 of 17 real-world layouts escape it (F2), and on
   Box2D the single escapee is `test/main.c`, the runner holding the
   `return 1;` that the recorded C-adapter incident was about. Classified as
   *observation*, not *ruling*: no law is consulted about candidate
   eligibility at all — `find_candidate_files` filters before SIGHT is asked.
   Mitigation in place: `coracle.check()`'s exit-code cross-examination
   (`coracle.py:283-291`). Whether the mitigation is sufficient on that file
   is **unmeasured**.
4. **`acts.py:406` — observation (missing).** A truncated candidate set is a
   CAPPED situation the engine law is never told about (F5). Latent: the cap
   does not bite on the shipped vocabulary on 23,194 measured lines.
5. **`oracle.py:120` / `coracle.py:102` — observation.** A candidate that
   overruns `timeout` returns `(1, "TIMEOUT")` (`oracle.py:160-161`) and is
   counted as a rejection, so `acts_tried` fills and `decide(situation(
   REFUTED=True))` rules HARVEST_COUNTEREXAMPLE. A clock expiry is being
   reported to the law as "the suite rejected it". The honest bit is CAPPED.
6. **No test pins any census constant** (F7). Not a wrong outcome, so not a
   defect under the brief's four categories — recorded because it is why 1-5
   could drift without anything going red.

No defect found in any **ruling**. Every law I exercised (SIGHT over its
eight bits, RANK over eight, ENGINE over the six the body can construct) ruled
consistently with its own docstring on every input I gave it.

## 7. Verdict

Every outcome-changing constant in the body is a threshold or name list
standing in for a law bit the body measures approximately — 22 feeding a law
bit, 16 gating an outcome with no owning bit, 13 fixed name lists, and not one
pinned by a test; two of them (`guard.py:591-592`'s starvation cap, silently
inert in the default path, and `guard.py:111-115`'s four-spelling whitelist,
which lets Box2D's own test runner into the candidate set) are wrong today,
both as observation/actuation defects and neither as a ruling.
