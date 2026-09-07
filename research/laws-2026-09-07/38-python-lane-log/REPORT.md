# 38-python-lane-log

## 1. Target
Run the guard on every Python fixture under `tests/`, log every law ruling, and produce a table of lanes hit against outcomes — plus the set of engine-law observation bytes the body can actually construct.

## 2. Method

Nothing in `src/`, `tests/` or `docs/` was edited and no git state was changed. Every run went through `./tmo.sh 300 ...`, which is `nice -n 15` + a `perl` `alarm(N)` wrapper (this machine has no coreutils `timeout`); test files were run **one at a time**.

Files kept next to this report so a human can rerun everything:

| file | what it is |
|---|---|
| `tmo.sh` | the nice + perl-alarm timeout wrapper (verified: `rc=124` on a spin loop) |
| `lanelog_plugin.py` | pytest plugin (`-p lanelog_plugin`) that rebinds the law entry points **in memory** and logs every consultation with its call site |
| `run_all.sh` | the per-file runner |
| `analyse.py` -> `analysis.txt` | reduces `logs/*.jsonl` to the lane tables |
| `bytes_constructible.py` -> `constructible.txt` | static enumeration of the constructible engine bytes + tautology check |
| `tiebreak.py` -> `tiebreak.txt` | how much of the ORDER the laws actually decided |
| `counterfactual_plugin.py` -> `counterfactual.txt` | suppresses the one live guard-level ruling and re-runs the test |
| `fixture_table.txt`, `codepath.txt` | the per-fixture lane table and the code-vs-law reason census |
| `logs/*.jsonl`, `logs/*.out` | raw log, one file per test file |

The instrumentation patches `fluidfix.engine.decide`, `fluidfix.loop.decide` (loop binds it at import), `fluidfix.sight.sight`, `fluidfix.rank.rank`, `fluidfix.router.route`, `fluidfix.acts.route`, `fluidfix.lanes.{EMIT,ADVANCE,HALT}` + their `loop` bindings, and wraps `guard_once` / `repair` for fixture identity and outcome. The call site is taken from the live stack, so a body consultation is separable from a test's own direct call to a law.

Test files run (all passed under instrumentation):
`test_guard test_acts test_dictionary test_e2e test_dry_run test_refusal_diagnosis test_one_example_generalises test_context_transforms test_teaching test_engine_fusion test_harness_errors test_regressions test_demo_walkthrough test_estimate test_hotspots test_cli test_init test_packaging test_lanes test_rank_law test_sight_law test_router_law test_pair_law test_law_never_ruled_wrong test_span_edits`.
`tests/test_c_adapter.py` and `tests/test_java.py` were **not** run: their fixtures are C and Java, which are agents 36/37/39's targets.

`cli.py` is excluded from the "body" filter throughout: `fluidfix selfcheck` re-derives all 256 inputs of every law as verification, which is not a repair decision and swamps the census (it accounts for 52,656 of the 66,402 logged consultations).

**Measurement hazard removed.** My first pass passed `--basetemp` inside the fluidfix work tree. Fixture roots then sat inside a git repo, so `git -C <root> log/blame` returned *fluidfix's* history and the RECENT/TOUCHED bits fired spuriously; `tests/test_hotspots.py::test_not_a_git_repo_answers_instead_of_raising` failed for the same reason. All numbers below come from the re-run with pytest's default (non-git) basetemp, where that test passes. There are no `tests/__pycache__` writes: `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.

## 3. Findings

### F1 — 43 guard passes on Python fixtures: 29 repaired, 10 refused, 4 green

```
$ ./run_all.sh <25 test files>          # then:
$ .venv/bin/python analyse.py
guard_once runs on Python fixtures: 43
Counter({'repaired': 29, 'refused': 10, 'green': 4})
...
total guard wall seconds: 527.1
candidate-file count histogram: {1: 39, 0: 4}
```

The full per-fixture table is `fixture_table.txt` (summarised in section 4). No run raised, none timed out.

### F2 — the body constructed only **5** distinct engine bytes; at most **10 of 256** are constructible at all

Measured, from the body only:

```
site             byte bits                         ruling                         n
loop.py:217    0x01   BUILT                        SHIP                          34
guard.py:539   0x40   REFUTED                      HARVEST_COUNTEREXAMPLE         5
guard.py:618   0x40   REFUTED                      HARVEST_COUNTEREXAMPLE         5
guard.py:539   0x00   (none)                       SHIP                           3
loop.py:217    0x03   BUILT|AMB                    ADD_STATE                      3
guard.py:539   0x60   CAPPED|REFUTED               RAISE_BUDGET                   2

distinct engine bytes the body constructed: [0, 1, 3, 64, 96]
engine consultations from the body        : 52
per-site counts: {'loop.py:217': 37, 'guard.py:539': 10, 'guard.py:618': 5}
```

Static enumeration over the six call sites (`bytes_constructible.py`) gives the whole constructible set, this corpus or any other:

```
distinct bytes constructible : 10 of 256 (3.9%)
bytes                        : ['0x00','0x01','0x03','0x04','0x10','0x20','0x21','0x23','0x40','0x60']
distinct rulings reachable   : 6 of 8 -> ['ADD_MATERIAL','ADD_STATE','CHANGE_GRANULARITY',
                                          'HARVEST_COUNTEREXAMPLE','RAISE_BUDGET','SHIP']
acts NEVER reachable         : ['RESHAPE', 'AUTHOR_SUCCESSOR']
```

`0x21` (BUILT|CAPPED) and `0x23` (BUILT|AMB|CAPPED) are constructible — `_rule(capped=True)` at `loop.py:272` and `loop.py:291`, the two deadline paths — but were never reached in this corpus (no fixture expired a deadline with a green already in hand). **This is the deliverable the census asked for: the body's whole engine vocabulary is ten bytes, and it spoke five of them.**

### F3 — three of the six call sites never fired at all

`guard.py:491` (UNREAD) never fired: `pytest-cov` is installed in `.venv`, so `_has_pytest_cov()` is always true.
`guard.py:612` (REFUTED inside the escalation branch) never fired: no fixture both escalated and exhausted every escalated candidate.
`loop.py:391` (HIDDEN) never fired: no Python fixture under `tests/` is flaky, so no green ever failed its re-check.

### F4 — the census's shape is confirmed exactly: 3 tautologies, 1 decoration, 2 live

```
$ .venv/bin/python bytes_constructible.py
guard.py:491   TAUTOLOGY: single literal byte, ruling is always ADD_MATERIAL, the == test can never be False
guard.py:539   LIVE: 3 distinct rulings possible -> ['HARVEST_COUNTEREXAMPLE', 'RAISE_BUDGET', 'SHIP']
guard.py:612   TAUTOLOGY: single literal byte, ruling is always HARVEST_COUNTEREXAMPLE, the == test can never be False
guard.py:618   TAUTOLOGY: single literal byte, ruling is always HARVEST_COUNTEREXAMPLE, the == test can never be False
loop.py:217    LIVE: 3 distinct rulings possible -> ['ADD_STATE', 'RAISE_BUDGET', 'SHIP']
loop.py:391    DECORATIVE: ruling is interpolated into a message, nothing branches
```

The three tautologies are `decide(situation(K=True)) == <the act K always rules>`; the comparison has no false branch. `loop.py:391`'s ruling only lands in the `why` string. The two live sites are the only places an engine ruling can move an outcome.

### F5 — `guard.py:539` is load-bearing: suppressing its ruling turns a repair into a refusal

Counterfactual: rebind `decide` so that any `RAISE_BUDGET` returned to a `guard.py` frame becomes `HARVEST_COUNTEREXAMPLE`. `loop.py`'s consultations are left honest. Nothing in `src/` is edited.

```
$ PYTHONPATH=<dir> ./tmo.sh 300 .venv/bin/python -m pytest \
    tests/test_engine_fusion.py::test_capped_escalation_raises_budget_and_repairs \
    -q -p counterfactual_plugin
        report = guard_once(oracle, MechanicalObserver())
>       assert report.status == "repaired"
E       AssertionError: assert 'refused' == 'repaired'
----------------------------- Captured stdout call -----------------------------
[cf] suppressing RAISE_BUDGET at guard.py:539 (byte 0x60)
1 failed in 23.97s
```

The same site ruled `RAISE_BUDGET` on 0x60 twice in the corpus (`test_capped_escalation_raises_budget_and_repairs`, `test_budget_hands_first_pass_over_to_escalation`) — both repaired. It ruled non-escalating on the other 8 calls. So this site's ruling changed the outcome in **2 of 10** consultations.

### F6 — `loop.py:217` is load-bearing: 34 SHIP vs 3 ADD_STATE

37 consultations dispatch on the ruling: 34 `0x01 -> SHIP` (write the repair) and 3 `0x03 -> ADD_STATE` (refuse as ambiguous). Both branches are exercised by real fixtures (`test_ambiguous_greens_refuse_with_add_state`, `test_two_green_spans_refuse_ambiguous`). This is the one site where the engine law's answer is *dispatched on* rather than compared to a constant.

### F7 — on the refusal path the body asks the law with an **empty** byte, and the law answers `SHIP`

Three refusals reached `guard.py:539` with byte `0x00` (`capped0=False, acts0=False`) and the law ruled `SHIP` (`analysis.txt`, and `constructible.txt`: `0x00 (none) -> SHIP`). The body only asks `== "RAISE_BUDGET"`, so `SHIP` is discarded and behaviour is correct. But the situation being reported is false: the suite is red and nothing was built. The true situation — "the vocabulary named no kind, so no candidate was ever generated" — has **no bit in `BITS`**. `REFUTED` is defined as *candidates were generated and the suite rejected every one*, which is a different fact; `0x00` is what is left. Those three runs are `test_dry_run_refusal_behaves_exactly_as_today`, `test_guard_refuses_novel_class_loudly_and_untouched`, `test_global_budget_is_an_honest_stop`, and all three return a `GuardReport` with an empty `hint` (`codepath.txt`).

### F8 — 18 of 55 `repair()` calls (32.7%) never consulted the engine law at all

```
repair() calls on Python fixtures: 55
  reason carries an engine-law ruling (law consulted): 37
  reason written by CODE, law never consulted        : 18
  code-written reasons seen:
      10  every candidate left the suite red — fault is outside this vocabulary or the obs...
       6  no observation named a kind this vocabulary can repair
       1  no failing test — nothing to repair
       1  wall-clock deadline reached mid-search — remaining observations untried
```

Cause: `loop.py:194` `if not greens: return None` inside `_rule` — the law is only asked when something is green. Every no-green exit falls through to a hand-written reason at `loop.py:425-429` and `loop.py:275/289`. The guard *does* later ask about REFUTED at `:539`/`:618`, so the outcome is not wrong; the **wording of the report at the loop level is code-decided**, and the two reasons it distinguishes ("no kind named" vs "all candidates red") are exactly the distinction `BITS` cannot express (F7).

### F9 — the `if not hint` precedence at `guard.py:618` is a code decision the law is never asked about

`guard.py:491` may set `hint` (UNREAD); `guard.py:618` sets the REFUTED hint only `if not hint`. So when UNREAD and REFUTED are both true the body constructs neither `0x04` nor `0x40` together — byte `0x44` is never built. The law does have a ruling for it:

```
0x44  UNREAD|REFUTED         -> law rules ADD_MATERIAL   (guard.py: `if not hint` — code precedence, law never asked)
```

The code's choice (prefer the UNREAD message) **agrees** with the law's `ADD_MATERIAL`. It is a correct decision reached without consulting the law that already owns it. Unmeasured in this corpus: `guard.py:491` never fired (F3), so the precedence was never exercised.

### F10 — the `escalate and ...` code veto at `guard.py:539` is never exercised anywhere

```
$ grep -rn "escalate=" tests/*.py src/fluidfix/cli.py
(no output)
$ sed -n '111,114p' src/fluidfix/cli.py
        report = guard_once(oracle, observer, coverage_target=args.cov,
                            candidate_timeout=args.candidate_timeout,
                            escalate_budget=args.escalate_budget,
                            budget=args.budget)
```

`escalate` keeps its default `True` in the CLI and in every test. A code flag sits in front of the law's only live guard-level ruling and nothing ever sets it.

### F11 — the SIGHT law was consulted 38 times and ordered nothing, 38 times out of 38

```
SIGHT LAW — bytes the body constructed (guard.py:280)
guard.py:280   0x5a  SCARCE|FAILONLY|NAMED|SMALL            prio=0   n=22
guard.py:280   0x58  FAILONLY|NAMED|SMALL                   prio=2   n=6
guard.py:280   0x7a  SCARCE|FAILONLY|NAMED|TOUCHED|SMALL    prio=0   n=5
guard.py:280   0x1a  SCARCE|FAILONLY|NAMED                  prio=0   n=4
guard.py:280   0x52  SCARCE|NAMED|SMALL                     prio=0   n=1
SIGHT bits never observed set: ['FRAMED', 'LITERAL', 'UBIQUITOUS']
distinct sight priorities emitted: [0, 2]
```
```
SIGHT — guard.py:280 (FILE order)
sorts observed                : 38  (38 elements)
sorts with >1 element         : 0
```

Every Python fixture in `tests/` is a two-to-seven-file toy with exactly **one** candidate source file (F1: candidate histogram `{1: 39, 0: 4}`). A one-element sort is order-free, so SIGHT's priority could not have changed any outcome here. `FRAMED` never set is notable: `test_guard_follows_traceback_frames` is a raising fault whose traceback names `mod.py`, and `mod.py` is nonetheless not in `framed_files` for the SIGHT call. Whether that is a mismeasurement of FRAMED or an artefact of the single-candidate path is **unmeasured** — it needs a multi-file fixture, which is agent 17/20's target.

### F12 — the ranking law's answer is uniform on 98.9% of lines; the code tiebreak decides 63.6% of the multi-line sorts

```
RANK — guard.py:406 (LINE order)
sorts observed                : 41  (1904 elements)
sorts with >1 element         : 33
  ...where the law gave ONE priority to every element
     (order decided ENTIRELY by the code tiebreak) : 21  (63.6%)
  ...where the law separated at least two elements : 12  (36.4%)
priority histogram            : {0: 11, 2: 6, 3: 1883, 7: 4}
modal priority 3 covers        : 1883 of 1904 elements (98.9%)

guard.py:406   0x68  SIGNALED|CHEAP|DENSE      prio=3   n=1818
RANK bits never observed set: ['FAILONLY', 'RETRIED']
```

`sorted(key=(priority(obs), -_tokens(obs), i))` at `guard.py:425-427`: when the law returns one class for every line, the whole order comes from `-_tokens` and then the original index — code. `FAILONLY` is never measured (documented in the `rank_observations` docstring). `RETRIED` — the law's **veto**, the bit the module docstring says the law exists for — was never set in 1,904 consultations on this corpus.

### F13 — router and lanes: exercised, single worked example, no surprises

```
route() calls from the body: 3956
distinct (F1,A1,Fq) queried: [(0,5,0) ... (0,5,12), (0,5,14)]      # F1=0, A1=5 always
distinct act codes returned: [0,1,3,5,6,7,8,9,10,11,12,13,14,15]
lanes calls from the body: {'lanes.HALT': 3870, 'lanes.EMIT': 1963, 'lanes.ADVANCE': 1963}
distinct HALT results: [0, 1]
distinct EMIT results: [1,2,4,8,16,32,64,256,512,1024,2048,4096,16384]
```

`HALT` returned both 0 and 1; `EMIT`/`ADVANCE` are paired 1963/1963, i.e. every emitted bit was cleared — the mask strictly reduces on every fixture, which is the termination property. Kind 13 (`0,5,13`) was never queried; act codes 2 and 4 never returned.

## 4. Lanes

### Engine law — lanes hit against outcomes (43 guard passes)

`@l217` = `loop.py:217`, `@g539`/`@g618` = `guard.py:539`/`:618`. Full table in `fixture_table.txt`.

| outcome | n | engine bytes -> rulings seen | sight prio | rank prios |
|---|---|---|---|---|
| repaired | 27 | `0x01 -> SHIP @l217` | 0 or n/a | 0,2,3 |
| repaired (escalated) | 2 | `0x60 -> RAISE_BUDGET @g539`, then `0x01 -> SHIP @l217` | 0 | 3 |
| refused (ambiguous) | 2 | `0x03 -> ADD_STATE @l217` | 0 | 3 |
| refused (all candidates red) | 5 | `0x40 -> HARVEST_COUNTEREXAMPLE @g539` and `@g618` | 0 or 2 | 0,2,3 |
| refused (nothing generated) | 3 | `0x00 -> SHIP @g539` (discarded) | 0 or 2 | – or 3 |
| green | 4 | law never consulted | – | – |

**Lanes reached.** Engine: `BUILT`, `AMB`, `CAPPED`, `REFUTED` — acts `SHIP`, `ADD_STATE`, `RAISE_BUDGET`, `HARVEST_COUNTEREXAMPLE` (4 of 8). SIGHT: `SCARCE`, `FAILONLY`, `NAMED`, `TOUCHED`, `SMALL`; priorities 0 and 2. RANK: `FRAME`, `NAMED`, `SIGNALED`, `RECENT`, `CHEAP`, `DENSE`; priorities 0, 2, 3, 7. Router: 14 of 16 kinds. Lanes: `EMIT`/`ADVANCE`/`HALT` on masks up to bit 14.

**Lanes never reached, and the observation each needs.**

| lane | why not reached here | observation that would reach it |
|---|---|---|
| engine `UNREAD` -> `ADD_MATERIAL` | `pytest-cov` installed in `.venv` | a target interpreter without `pytest-cov`; the site is a tautology, so the ruling is already fixed |
| engine `HIDDEN` -> `CHANGE_GRANULARITY` | no flaky Python fixture in `tests/` | a test that skips its assert some of the time — `loop.py:391` would then fire (agent 05's target) |
| engine `NOTWIN`, `SELF` | never measured anywhere in the body | not constructible today; nothing in `situation(**bits)` passes them |
| engine `RESHAPE`, `AUTHOR_SUCCESSOR` | **no constructible byte rules them** (F2) | unreachable by construction, not by fixture choice |
| engine `0x21`/`0x23` (BUILT+CAPPED) | no fixture hit a deadline holding a green | a deadline that expires between observations with one green found: `loop.py:272`/`:291` |
| SIGHT `FRAMED`, `LITERAL`, `UBIQUITOUS`; priorities 1,3,4,5,6,7 | every fixture has exactly one candidate file | a multi-file repo — Box2D/cglm/click scale, not `tests/` |
| RANK `FAILONLY` | not measured at all (`rank_observations` never passes `failonly=`) | line-level coverage of the passing set as well as the failing set |
| RANK `RETRIED` (the veto) | the retried set is empty on one-pass fixtures | a second pass over a file already tried |
| router kind 13 | `_swap_minmax` never selected | an observation naming kind 13 |

## 5. Potential

- **`RESHAPE` and `AUTHOR_SUCCESSOR` are unreachable by construction, not by accident.** No byte in the ten-byte constructible set rules them (F2). Reaching either needs a *new observation bit set*, not a new fixture. What they would be worth is **unmeasured**.
- **The empty-byte refusal (F7).** Three of ten refusals in this corpus put a false situation (`0x00`) to the law. A bit distinguishing "no candidate was ever generated" from `REFUTED` would let the law rule on the commonest refusal shape fluidfix has, instead of receiving silence and answering `SHIP`. Value: it would convert 3 of 43 passes (7.0%) from a hintless refusal into a law-ruled one. Whether the ruling would then differ from today's behaviour is **unmeasured**.
- **`RETRIED`, the ranking law's own headline veto, was set 0 times in 1,904 consultations.** The 1,934s/474-candidate click incident the module docstring cites is exactly the case it exists for, and no fixture under `tests/` is large enough to produce it. The Python fixture corpus cannot exercise it; a real repo can (agents 17/25).
- **The line order is 63.6% code.** On 21 of 33 multi-line sorts the law returned one class for everything and the tiebreak `(-shared_tokens, original_index)` decided alone. The law's discrimination is limited by `DENSE` firing on 1,818 of 1,904 lines: byte `0x68` (`SIGNALED|CHEAP|DENSE`) is 95.5% of all consultations. Whether a `DENSE` threshold other than `>= 8` would separate these lines is **unmeasured**.
- **SIGHT is untested by this corpus.** 38 consultations, 0 orderings. Any claim about SIGHT's value has to come from a multi-file repo.

## 6. Defects

**None found in any ruling.** Every ruling logged matches `engine.decide` / `sight.sight` / `rank.rank` / `route` on the byte the body supplied, and every outcome follows from the ruling the body received.

Three findings classify as **observation** or **wording**, none as a wrong ruling:

1. **Observation (F7).** `guard.py:539` builds `0x00` on the "nothing was generated" refusal path. `BITS` has no lane for that fact, so the body reports the empty situation and the law — ruling correctly on what it was given — answers `SHIP`. Harmless today only because the body compares to a string constant instead of dispatching on the ruling. Anyone who later turns `guard.py:539` into a dispatch (as `loop.py:217` already is) would ship a repair on a red suite. *The law was not wrong; the situation was not measured.*
2. **Wording (F8).** 18 of 55 `repair()` exits report a reason no law authored, because `_rule` returns `None` before consulting anything when `greens` is empty (`loop.py:194`). The two reasons the code writes are precisely the distinction the engine's `BITS` cannot express, so this is the same gap as (1) seen at the loop level.
3. **Actuation/code decision (F9, F10).** Two outcome-affecting decisions are made by code beside the law: the `if not hint` precedence at `guard.py:618` (byte `0x44` never built; the law would rule `ADD_MATERIAL`, which is what the code does anyway) and the `escalate and` veto at `guard.py:539`, which nothing in the shipped body ever sets to `False`.

## 7. Verdict
Across 43 guard passes on the Python fixtures the body spoke five distinct engine bytes of a ten-byte constructible vocabulary and never ruled wrong; two of the six `decide()` calls are live and both are load-bearing (suppressing `guard.py:539`'s `RAISE_BUDGET` flips a repair to a refusal), while SIGHT ordered nothing in 38 consultations, the ranking law's `RETRIED` veto fired 0 times in 1,904, and the commonest refusal shape reaches the law as an empty byte the law can only answer `SHIP`.
