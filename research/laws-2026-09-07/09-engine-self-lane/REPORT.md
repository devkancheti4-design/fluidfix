# 09-engine-self-lane

## 1. Target
The engine law's SELF bit (bit 7): what it means, whether fluidfix's body can measure it today, what `decide()` rules for all 128 SELF combinations, and a report-only design for the observation.

## 2. Method
Read, in `/Users/kanchetidevieswar/neo/fluidfix/`:
`src/fluidfix/engine.py` (docstring + `LAW` + `situation`/`decide`), `src/fluidfix/loop.py` (lines 199-400), `src/fluidfix/guard.py` (lines 105-180, 439-620), `src/fluidfix/acts.py`, `src/fluidfix/cli.py` (lines 470-480, 605-730), `tests/test_engine_fusion.py`.
Read the upstream authoring repo's own documentation, fetched read-only by an earlier attempt in this session into `09-engine-self-lane/dev_repo/` (`ENGINE_LAW.py`, `ENGINE_HOWTO.md`) plus `dev_README.md` and `dev_tree.txt`.

Scripts in this directory (all rerunnable; all pure arithmetic except `body_bytes_probe.py`, which runs three tiny pytest fixtures in temp dirs it deletes):

| script | what it measures | output |
|---|---|---|
| `self_table.py` | ruling for all 128 SELF=1 bytes, paired with SELF=0 | `self_table.out` |
| `algebra_check.py` | closed form of the law vs the vendored formula, 1024 inputs | `algebra_check.out` |
| `constructible_bytes.py` | every byte the body can build, from its `situation()` call sites | `constructible_bytes.out` |
| `body_bytes_probe.py` | bytes the body actually hands the law during real guard runs | `body_bytes_probe.out` |
| `events_check.py` | the 22 upstream authoring events re-ruled through the vendored law | `events_check.out` |
| `self_observation_design.py` | the proposed SELF predicate, computed on real paths | `self_observation_design.out` |

`nice -n 15` was used on every run. **The machine has no `timeout` binary** (`which timeout gtimeout` -> `timeout not found`), so the brief's `timeout 300` was substituted with `nice -n 15 perl -e 'alarm 300; exec @ARGV' <cmd>`, which enforces the same 300 s wall-clock ceiling. Stated here because the brief named the tool.

Every prior-attempt output was re-run this session and confirmed byte-identical (`diff` against the stored `.out`): `algebra_check.py`, `constructible_bytes.py`, `body_bytes_probe.py`, `fluidfix selfcheck`.

## 3. Findings

### F1. SELF means "the job IS the worker" — and its authored act is AUTHOR_SUCCESSOR
The bit table lives in the authoring repo's README, copied read-only to `dev_README.md`:

```
| 7 | SELF — the job *is* the worker | AUTHOR_SUCCESSOR |
```

The five authoring events that carry SELF are in `dev_repo/ENGINE_LAW.py`; `events_check.py` re-rules all 22 through fluidfix's vendored `decide()`:

```
$ .venv/bin/python events_check.py
reproduced under fluidfix's vendored law: 22/22
the SELF events, with the authoring note:
  REVIEW_PR  BUILT+SELF       -> SHIP
      the certificate's own self-test passed and it shipped     [8/8]
  REVIEW_PR  REFUTED+SELF     -> HARVEST_COUNTEREXAMPLE
      the audit refuted verify_witness, the module's OWN checker [audit]
  DEBUG      CAPPED+SELF      -> RAISE_BUDGET
      the harness hit its own 5GB ceiling -> raised to 6GB       [tight3]
  DEBUG      UNREAD+SELF      -> ADD_MATERIAL
      the harness lacked the shift primitives it had to supply   [duel_supply]
  WRITE_CODE NOTWIN+SELF      -> AUTHOR_SUCCESSOR
      Law-C exists but not in a form covering four jobs -> AUTHOR THIS SUCCESSOR
```

### F2. SELF changes the ruling on exactly 2 of 128 bytes
`self_table.py` prints all 128 SELF=1 bytes beside the same byte with SELF cleared:

```
=== bytes where setting SELF changes the ruling: 2 of 128 ===
  135  BUILT+AMB+UNREAD+SELF     ADD_STATE -> RAISE_BUDGET
  136  NOTWIN+SELF               RESHAPE   -> AUTHOR_SUCCESSOR
```

On the other 126 bytes SELF is inert. Ruling distribution over the SELF half is nearly identical to the non-SELF half (`self_table.out`): ADD_STATE 56 vs 57, RESHAPE 8 vs 9, AUTHOR_SUCCESSOR 8 vs 7, everything else equal.

### F3. Why, algebraically — SELF is deliberately excluded from the second term
`algebra_check.py` proposes a closed form and checks it on all 1024 inputs (256 bytes x 4 job values):

```
act = (4 if (x & 15) in {7, 8} and (x & 0xF0) else 0) + ntz(x & 0x7E)   (mod 8)

$ .venv/bin/python algebra_check.py
inputs checked: 1024 (256 bytes x job 0..3); mismatches: 0
bytes where SELF flips the ruling: 2 -> [7, 8]
```

`x + (x & 128)` doubles bit 7 into bit 8, so the second term's `& 254` mask never sees SELF: SELF cannot be the "first blocking observation". Its only route into the ruling is the `x - 7` borrow in the first term, where it is **interchangeable with HIDDEN, CAPPED and REFUTED**:

```
NOTWIN+HIDDEN   -> AUTHOR_SUCCESSOR   BUILT+AMB+UNREAD+HIDDEN   -> RAISE_BUDGET
NOTWIN+CAPPED   -> AUTHOR_SUCCESSOR   BUILT+AMB+UNREAD+CAPPED   -> RAISE_BUDGET
NOTWIN+REFUTED  -> AUTHOR_SUCCESSOR   BUILT+AMB+UNREAD+REFUTED  -> RAISE_BUDGET
NOTWIN+SELF     -> AUTHOR_SUCCESSOR   BUILT+AMB+UNREAD+SELF     -> RAISE_BUDGET
```

### F4. SELF is not a brake — the law ships on it
```
$ .venv/bin/python algebra_check.py
SELF alone         -> SHIP
BUILT+SELF         -> SHIP
BUILT+AMB+SELF     -> ADD_STATE
SELF+REFUTED       -> HARVEST_COUNTEREXAMPLE
```
"The job is the worker" is not, to this law, a reason to stop. It matches the authoring note for `BUILT+SELF`: *the certificate's own self-test passed and it shipped*. This matters for the design in F8.

### F5. The body has seven `situation()` call sites and none of them passes SELF
```
$ grep -n "situation(" src/fluidfix/*.py     # engine law sites only
src/fluidfix/cli.py:474    decide(situation(**{k: True}))  for BUILT/AMB/UNREAD/CAPPED/REFUTED
src/fluidfix/guard.py:491  situation(UNREAD=True)
src/fluidfix/guard.py:539  situation(CAPPED=capped0, REFUTED=acts0)
src/fluidfix/guard.py:612  situation(REFUTED=True)
src/fluidfix/guard.py:618  situation(REFUTED=True)
src/fluidfix/loop.py:217   situation(BUILT=True, AMB=..., CAPPED=...)
src/fluidfix/loop.py:391   situation(HIDDEN=True)
```
(`sight.py:118`, `pair.py:144`, `rank.py:83` are other laws' own `situation()`.) `SELF` appears in `src/` only in `engine.py`'s `BITS` list, `engine.py`'s docstring, and a comment at `loop.py:367`.

Measured at runtime, not just by reading — `body_bytes_probe.py` rebinds `decide` in `fluidfix.engine` and `fluidfix.loop` (no `src/` edit) and logs every byte three real guard runs hand the law:

```
--- AMB (two greens in one set): status=refused
    asked byte   3 (BUILT+AMB)  -> ADD_STATE
--- single green (strictness): status=repaired
    asked byte   1 (BUILT)      -> SHIP
--- REFUTED (fault out of vocabulary): status=refused
    asked byte  64 (REFUTED)    -> HARVEST_COUNTEREXAMPLE   (x2)

distinct bytes asked across the three runs: [1, 3, 64]
any byte with SELF (128) set: False
```

### F6. Even a perfect SELF observation would change nothing today
`constructible_bytes.py` enumerates all 11 bytes the seven call sites can produce and OR-s SELF into each:

```
constructible bytes today: 11; rulings SELF would change: 0
bytes on which SELF is live (from algebra_check): 7 (BUILT+AMB+UNREAD) and 8 (NOTWIN)
  byte 7 constructible today: False   byte 8 constructible today: False
```
Confirmed independently by `self_observation_design.py` over the same 11 bytes: `rulings changed: 0 of 11`.

SELF is live only in the company of another bit:
- **byte 8 (NOTWIN)** — NOTWIN is measured nowhere in `src/`.
- **byte 7 (BUILT+AMB+UNREAD)** — each of the three is measured somewhere, but no call site passes all three in one `situation()`. `loop.py:217` has BUILT+AMB but not UNREAD; `guard.py:491` has UNREAD alone.

### F7. Neither act SELF can reach is actuated, and no test pins any SELF byte
```
$ grep -rn "AUTHOR_SUCCESSOR" src tests docs CHANGELOG.md | grep -v src/fluidfix/engine.py
(no output)
$ grep -rn "RESHAPE" src tests docs CHANGELOG.md | grep -v src/fluidfix/engine.py
(no output)
```
Both acts exist only as strings in `engine.py:38-39`. `self_table.out` shows AUTHOR_SUCCESSOR is the law's ruling on 15 of 256 bytes (8 of them SELF bytes); none is reachable and none is actuated.

Test coverage of the SELF half is zero. `tests/test_engine_fusion.py:25-30` pins six bytes, all SELF=0. `selfcheck` pins five (`cli.py:472-473`: BUILT, AMB, UNREAD, CAPPED, REFUTED):
```
$ .venv/bin/fluidfix selfcheck
engine law rulings the guard depends on:      5/5
SELFCHECK PASS — 6 laws re-derived
```
So **0 of the 128 SELF bytes are pinned by fluidfix's own suite**; the only SELF rulings pinned anywhere are the five upstream authoring events, and only by `events_check.py` in this directory.

### F8. Design (report only): a mechanical SELF predicate, and why substituting it for today's filter would be a regression
`self_observation_design.py` implements three disjoint predicates, each computable from values `guard_once()` already holds (`oracle.root`, the candidate file path, `fluidfix.__file__`) — no new tooling, no LLM:

- **S1 SELF_TARGET** — the tree under repair contains the running `fluidfix` package.
- **S2 SELF_ORACLE** — the candidate file is part of the suite that adjudicates it (`test_*.py`, `*_test.py`, `conftest.py`).
- **S3 SELF_LAW** — the candidate file is one of the six vendored law modules.

Measured:
```
case                                      S1  S2  S3  SELF
ordinary repo, source file                 0   0   0     0
ordinary repo, its OWN test file           0   1   0     1
fluidfix pointed at itself, src            1   0   0     1
fluidfix pointed at itself, LAW            1   0   1     1
Box2D-style repo (no fluidfix inside)      0   0   0     0
```
Nothing stops S1 arising in the world: `cli.py:684/693/707/727` default `root` to `"."` and `cli.py:616` takes it positionally, so `fluidfix guard .` inside the fluidfix checkout is a supported invocation.

The S2 case is **already decided in code, not by the law**:
```
$ sed -n '111,115p;139p;170p' src/fluidfix/guard.py
def _is_test_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    base = parts[-1]
    return (base.startswith("test_") or base.endswith("_test.py")
            or "tests" in parts[:-1] or base == "conftest.py")
        if _is_test_path(rel):                       # 139: drop from candidates
                    if _is_test_path(rel) or not rel.endswith(".py"):   # 170
```
Test files are dropped from the candidate set unconditionally. That is the SELF situation ("the repair would edit its own checker") resolved by a hardcoded exclusion.

**And it should stay that way.** Per F4, the law's ruling for `BUILT+SELF` is `SHIP`. Replacing `_is_test_path` with a SELF observation would *permit* a repair that greened the suite by editing the suite. The body's filter is strictly stronger than the law's ruling here, and this is the honest reading, not a defect: the authoring events set SELF on a worker whose self-test was trustworthy, which is not fluidfix's situation when the candidate edit *is* the test. The design's useful half is S1 and S3, where SELF is a genuine new fact the body does not currently record at all.

## 4. Lanes
**Reached by this work** (by direct arithmetic over all 256 bytes, in `self_table.out`): every SELF ruling — SHIP (2), ADD_STATE (56), ADD_MATERIAL (32), RAISE_BUDGET (12), AUTHOR_SUCCESSOR (8), RESHAPE (8), CHANGE_GRANULARITY (8), HARVEST_COUNTEREXAMPLE (2).

**Reached by the body during real runs** (`body_bytes_probe.out`): bytes 1, 3, 64 -> SHIP, ADD_STATE, HARVEST_COUNTEREXAMPLE. No SELF byte, ever.

**Never reached, and why:**
- **All 128 SELF bytes.** No `situation()` call site passes `SELF=` (F5). Observation needed: any of S1/S2/S3 in F8 wired into the call sites.
- **Byte 136 (NOTWIN+SELF -> AUTHOR_SUCCESSOR)**, the SELF lane the law was authored for. Needs *two* new observations: SELF **and** NOTWIN. NOTWIN ("exists, but not in the form needed") maps in fluidfix to: a fault whose repair kind is absent from the `KINDS` vocabulary in `acts.py` — today that situation is reported as REFUTED instead, which routes to HARVEST_COUNTEREXAMPLE.
- **Byte 135 (BUILT+AMB+UNREAD+SELF -> RAISE_BUDGET)**. Needs a call site that packs BUILT, AMB and UNREAD together; `loop.py:217` and `guard.py:491` measure them in separate places.
- **The acts AUTHOR_SUCCESSOR and RESHAPE**, on all 15 and 9 bytes respectively — no actuation exists anywhere in the repo (F7).

## 5. Potential
- **Wiring SELF alone: zero rulings change.** Measured: 0 of the 11 constructible bytes, and 0 of the 3 bytes observed in real runs, change under `| SELF` (F6). This is the sharpest number in the report and it is a negative one — SELF is not a cheap win.
- **SELF + NOTWIN together** would open byte 136 and the AUTHOR_SUCCESSOR lane: the law telling fluidfix that its own repair vocabulary is the thing that needs extending, rather than refusing the defect. Value **unmeasured** — it requires the NOTWIN observation (agent-independent) and an AUTHOR_SUCCESSOR actuation, neither of which exists.
- **S1 (fluidfix pointed at itself) as a recorded fact** costs one `os.path` comparison and is exact (measured above: 1/1 true positive, 0/3 false positives on the five cases). Its value today is **unmeasured**, because with the current constructible byte set it changes no ruling; it becomes worth something only once byte 7 or byte 8 is constructible.
- **The 128 unpinned SELF rulings.** Zero are pinned by `tests/` or `selfcheck` (F7). The five upstream authoring events pin five of them and all five reproduce under the vendored law (F1) — pinning those five in `tests/` would cost one test and is the only SELF work with a measured basis today.

## 6. Defects

**D1 — wording, `src/fluidfix/engine.py:27`.** The docstring reads:
```
NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set
```
HIDDEN **is** measured and set, since 2026-09-04. Evidence:
```
$ grep -n "situation(HIDDEN" src/fluidfix/loop.py
391:                            ruling = decide(situation(HIDDEN=True))
$ sed -n '365,370p' src/fluidfix/loop.py
                        # This is the first of the three lanes fluidfix never
                        # measured (NOTWIN, HIDDEN, SELF) to turn out to
                        # matter. Measured 2026-09-04 against a test that
                        # skips its assert half the time: ...
```
and byte 16 (HIDDEN) appears in the body's constructible set (`constructible_bytes.out`, site `loop.py:391`). Classification: **wording** — the law ruled nothing wrong; `loop.py` itself documents the change; only `engine.py`'s docstring, the sentence that also states SELF's status, was not updated. It is load-bearing because that sentence is the project's specification of which bits are live. The SELF and NOTWIN halves of the claim are correct and re-verified here.

**D2 — none found for SELF itself.** No wrong outcome attributable to the SELF lane exists, because the lane has never been entered: `body_bytes_probe.out` records `any byte with SELF (128) set: False`, and `constructible_bytes.out` shows no call site that could set it. A lane that never fires cannot have ruled wrong.

*Incidental, outside this target (noted, not investigated):* `src/fluidfix/guard.py:452` says the first pass "may spend at most half of it" while `guard.py:468` sets `first_deadline = t0 + budget / 3`; the comment at 469-473 explains the change to a third. That is wording, and belongs to target 06.

## 7. Verdict
SELF means "the job is the worker", changes the law's ruling on exactly 2 of 128 bytes (135 and 136) and neither is constructible by fluidfix today, so measuring SELF alone would change zero rulings — its only live partner bits are NOTWIN, which the body never measures, and a BUILT+AMB+UNREAD call site that does not exist; the lane has never fired and has therefore never ruled wrong, and the single defect found is stale wording at `engine.py:27` claiming HIDDEN is also unmeasured when `loop.py:391` measures it.
