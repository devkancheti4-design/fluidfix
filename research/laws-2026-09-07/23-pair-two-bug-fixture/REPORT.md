# 23-pair-two-bug-fixture — the PAIR law on a genuine two-bug program

## 1. Target

Build a genuine two-bug Python program (two independent faults, two failing
test groups, each fix reducing the failure count), run the single-edit guard
on it, compute the PAIR law's observation byte from the completed search, and
confirm the law rules PARTITION.

## 2. Method

Everything below lives in
`/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/23-pair-two-bug-fixture/`.
Nothing outside it was written; no git state was changed; every run was
`nice -n 15` under a 300s cap.

Read first: `src/fluidfix/pair.py` (its docstring is the specification),
`docs/PAIR_LAW_PROMPT.md` (incidents, R1-R5), `tests/test_pair_law.py`,
`src/fluidfix/loop.py`, `src/fluidfix/guard.py`, `src/fluidfix/oracle.py`,
`src/fluidfix/localize.py`, `src/fluidfix/acts.py`.

Built:

| path | what it is |
| --- | --- |
| `fixture/` | the two-bug program: `billing.py` (fault A, line 13, kind 3 flipped-additive), `inventory.py` (fault B, line 11, kind 10 flipped-comparison-direction), `tests/test_billing.py`, `tests/test_inventory.py`, own `pytest.ini` |
| `conftest.py` | `collect_ignore_glob = ["*"]` — keeps this deliberately RED fixture out of any pytest started from the fluidfix repo root (50 agents share the box). Verified: `pytest --collect-only research/laws-2026-09-07/23-pair-two-bug-fixture` -> `no tests collected in 0.01s` |
| `timeout.py` | a `timeout(1)` substitute: this machine has neither `timeout` nor `gtimeout` (`which gtimeout timeout` -> not found), so every run below is `nice -n 15 python timeout.py 300 -- ...` |
| `measure.py` -> `measure.out`, `measured.json` | baseline, each fix alone, the pair, a completed `guard_once` over both files, replay of every rejected candidate, per-failing-test coverage, the byte and the ruling |
| `measure2.py` -> `measure2.out`, `measured2.json` | why the body never opens the second file; enumeration of the COMPLETE single-edit space of both files; all 18 candidates run; 80 cross-site pairs swept; the byte re-derived from that completed search |
| `partition_sim.py` -> `partition_sim.out` | what the PARTITION ruling would be worth: the linear path done by hand with an edit the search itself already found, then the unmodified guard re-run |
| `fixture-guard-run/` | the tree the real `fluidfix guard` CLI ran against, with its `.fluidfix/last_refusal.json` |

Both faults are one token and inside the SHIPPED vocabulary (`acts.KINDS` 3
and 10), so the single-edit search genuinely proposes each true fix — that is
what makes EXHAUSTED and PARTIAL measurable rather than assumed.

## 3. Findings

### F1 — the fixture is a genuine two-bug program (R4's shape, not a compensating pair)

```
$ nice -n 15 .venv/bin/python timeout.py 300 -- .venv/bin/python measure.py     # measure.out
STEP 1  baseline: the fixture as shipped (two independent faults)
  rc=1  failing=3
    tests/test_billing.py::test_invoice_total
    tests/test_billing.py::test_rounded_total
    tests/test_inventory.py::test_needs_reorder
STEP 2  each true single fix alone, and the pair (R4 / CANCELING)
  fix A alone (billing.py:13): failing 3 -> 1  ['tests/test_inventory.py::test_needs_reorder']
  fix B alone (inventory.py:11): failing 3 -> 2  ['tests/test_billing.py::test_invoice_total', 'tests/test_billing.py::test_rounded_total']
  fix A+B jointly: rc=0 failing=0
```

Each fix strictly REDUCES the failing count and the pair is green: exactly the
discriminator R4 names.

### F2 — the unmodified guard refuses, and its refusal names the wrong cause

```
$ nice -n 15 .venv/bin/python timeout.py 300 -- .venv/bin/fluidfix guard \
      .../23-pair-two-bug-fixture/fixture-guard-run --python .venv/bin/python
[14:19:14] REFUSED: fault is outside the taught vocabulary (candidate files tried: billing.py).
teach it once: docs/TEACHING.md (or run: fluidfix kinds) 3 candidate(s) were tried and rejected ...
  hint: every generated candidate was rejected by the suite (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE)
```

exit code 2 (`partition_sim.out`, GUARD PASS 1). The guard's own harvest log
contradicts the wording — `fixture-guard-run/.fluidfix/last_refusal.json`:

```json
{"at": "billing.py:13", "tried": "    return subtotal + tax",
 "why": "FAILED tests/test_inventory.py::test_needs_reorder - assert False is True"}
```

The true fix for fault A WAS in the vocabulary, WAS generated, and was
rejected by a test in a different module that the edit cannot reach. The
vocabulary was never the problem.

### F3 — the body cannot see the second fault file at all: its packet is empty

```
$ nice -n 15 .venv/bin/python timeout.py 300 -- .venv/bin/python measure2.py --pairs   # measure2.out
STEP A  why the body never opens the second fault file
  oracle.failing_output() runs pytest with -x; failing tests it names: ['tests/test_billing.py::test_invoice_total']
  (the suite actually has 3 failing tests)
  build_packet(billing.py   ) -> mode=coverage anchor_lines=[8, 12, 13, 16]   fault line 13 in packet: True
  build_packet(inventory.py ) -> mode=coverage anchor_lines=[]                fault line 11 in packet: False
```

The chain is all in the body: `Oracle.failing_output()` runs `-x`
(oracle.py:246), so the last-failed cache holds ONE test; `build_packet`
localises with `--lf` coverage (localize.py:137), so a file no cached failing
test executes gets zero anchor lines; zero anchors -> zero observations ->
zero candidates. Forcing the file list (`guard_once(..., files=["billing.py",
"inventory.py"])`, measure.out STEP 3) does not help: inventory.py still
produced no candidate.

### F4 — the COMPLETED single-edit search, measured over both files

`measure2.py` enumerates every candidate the shipped vocabulary proposes for
every line of both fault files (independent of the body's localisation) and
runs each against the suite:

```
STEP B  billing.py       8 candidates (5 distinct lines)
        inventory.py    10 candidates (4 distinct lines)
        TOTAL single-edit candidates: 18
STEP C  baseline failing: 3
    billing.py:13   kind 3  return subtotal + tax          3 -> 1  REDUCES [test_invoice_total, test_rounded_total]
    inventory.py:11 kind 10 return on_hand < reorder_point 3 -> 2  REDUCES [test_needs_reorder]
  18 candidates run in 3.5s (0.20s each)
  greens (a single edit that repairs the suite): 0
  strict reducers: 2 at sites [('billing.py', 13), ('inventory.py', 11)]
```

### F5 — the observation byte, bit by bit, and the ruling

| bit | value | how it was measured |
| --- | --- | --- |
| EXHAUSTED | 1 | all 18 single-edit candidates run, 0 green (F4); no budget or deadline stop |
| PARTIAL | 1 | 2 candidates strictly reduce, 3 -> 1 and 3 -> 2 (F4) |
| DISJOINT | 1 | the two reducing sites repair `{test_invoice_total, test_rounded_total}` and `{test_needs_reorder}`: pairwise disjoint, together all 3 failing tests. Independently confirmed by per-failing-test coverage — shared executed sites between the groups: NONE (measure.out STEP 5a) |
| COUPLED | 0 | more than one group (same measurement) |
| CHEAP | 1 | 18 candidates at a measured 0.20s/run; the whole naive pair space is 153 combinations ~30s. NO code in the body owns a CHEAP threshold — the law is never called (F9) — so "affordable" is my judgement from the measured numbers, and the ruling is reported both ways below |
| TAUGHT | 0 | no dictionary loaded; kinds 3 and 10 are shipped vocabulary, not taught from a worked example. Reported both ways |
| CANCELING | 0 | measured by exhaustive cross-site sweep, F6 |
| CAPPED | 0 | no `--budget` given; no deadline fired |

```
STEP 8  the observation byte and the law's ruling                    (measure.out)
    TAUGHT=False CHEAP=True  byte= 23 (0b00010111) EXHAUSTED|PARTIAL|DISJOINT|CHEAP  ->  0 PARTITION
    TAUGHT=False CHEAP=False byte=  7 (0b00000111) EXHAUSTED|PARTIAL|DISJOINT        ->  0 PARTITION
    TAUGHT=True  CHEAP=True  byte= 55 (0b00110111) ...|CHEAP|TAUGHT                  ->  0 PARTITION
    TAUGHT=True  CHEAP=False byte= 39 (0b00100111) ...|TAUGHT                        ->  0 PARTITION
```

THE LAW RULES PARTITION (act 0) on the measured byte 23, and on all four
readings of the two bits no code owns. Note that
`tests/test_pair_law.py::test_incident_two_independent_bugs_partition_first`
pins byte 55 (the TAUGHT variant); the byte a real mechanical run produces
here, 23, is covered only by the exhaustive spec test, not by a named
incident.

### F6 — the CANCELING veto is correctly NOT triggered (exhaustive sweep)

```
STEP E  cross-site pair sweep                                       (measure2.out)
  swept 80 cross-site pairs in 15.7s
  green pairs: 1
    return subtotal + tax  + return on_hand < reorder_point   members reduce alone: (True, True)
  CANCELING pairs (green jointly, neither member reduces): 0 []
```

Every cross-site pair of the completed space was run. Exactly one is green —
the true pair — and both its members reduce alone, so bit 6 is 0 by
measurement, not by assumption. R4 holds empirically here: the genuine
two-bug shape is distinguishable from the compensating one.

### F7 — what PARTITION is worth here: a refusal becomes a green suite

`partition_sim.py` does by hand exactly what PARTITION says, using only an
edit the search itself had already generated and rejected:

```
baseline: (1, '3 failed, 2 passed in 0.01s')
GUARD PASS 1 on the un-partitioned repo (exit 2, 2.9s):  REFUSED: fault is outside the taught vocabulary ...
after pass 1: (1, '3 failed, 2 passed in 0.01s')

PARTITION step 1 applied (billing.py:13 <- the search's own strict reducer): (1, '1 failed, 4 passed in 0.01s')
GUARD PASS 2 on the residue (exit 0, 2.7s):
   [14:24:06] inventory.py: repaired line 11 in 3 suite runs (1.3s):
     - return on_hand > reorder_point
     + return on_hand < reorder_point
after pass 2: (0, '5 passed in 0.01s')
```

The second fault, invisible to pass 1, is repaired in 3 suite runs / 1.3s
once the first group is out of the way. The tree ends green.

### F8 — sensitivity: which bits the ruling actually turns on

```
  sensitivity — what each unmeasured bit would cost:                 (measure.out)
    drop/add EXHAUSTED  byte  23 ->  22: PARTITION -> SINGLE
    drop/add PARTIAL    byte  23 ->  21: PARTITION -> PARTITION
    drop/add DISJOINT   byte  23 ->  19: PARTITION -> WIDEN
    drop/add COUPLED    byte  23 ->  31: PARTITION -> PARTITION
    drop/add CHEAP      byte  23 ->   7: PARTITION -> PARTITION
    drop/add TAUGHT     byte  23 ->  55: PARTITION -> PARTITION
    drop/add CANCELING  byte  23 ->  87: PARTITION -> REFUSE
    drop/add CAPPED     byte  23 -> 151: PARTITION -> CAPPED
```

and algebraically over all 256 inputs (`.venv/bin/python`, `fluidfix.pair`
imported directly):

```
PARTITION inputs: 16
EXH&PAR&DIS family: 32 -> {CAPPED, PARTITION, REFUSE}; minus CANCELING/CAPPED: 8 -> {PARTITION}
EXH|DIS (no PARTIAL) -> PARTITION      EXH|PAR|CHE (no DISJOINT) -> WIDEN
PAR|DIS|CHE (not EXHAUSTED) -> SINGLE  EXH|PAR|CHE|COU -> PAIR
```

So on this fixture only two observations carry the ruling: EXHAUSTED and
DISJOINT. Both are derivable from data the body ALREADY holds — the harvest
entry in F2 pairs a candidate site (`billing.py:13`) with the test that
killed it (`tests/test_inventory.py::test_needs_reorder`), and a killing test
the candidate's site cannot reach is the DISJOINT signal, at zero extra suite
runs.

### F9 — the law is fused, never actuated

```
$ grep -rn "pair_law\|from .pair\|import pair" src/ tests/ docs/ | grep -v ^src/fluidfix/pair.py
src/fluidfix/cli.py:527:    from .pair import pair_law as _pair          # selfcheck only
tests/test_pair_law.py: ...
```

No call site in `loop.py`, `guard.py`, `acts.py`, `oracle.py` or
`coracle.py`. Nothing in the body computes any of the eight bits.

## 4. Lanes

Reached by this work with a byte measured from a real search:

- PARTITION (act 0) — byte 23 measured; also 7, 39 and 55 under the two bits
  no code owns. It is the only lane this fixture's situation reaches.

Reached only by evaluating the law on constructed bytes (no measured
situation behind them): SINGLE (0, 22), WIDEN (19), PAIR (EXH|PAR|COU|CHE),
REFUSE (any CANCELING), CAPPED (151), BUDGET (EXH|TAU), TEACH (not exercised
at all beyond the 256-input sweep in F8's totals).

Never reached IN THE BODY, by anything, ever: all eight. `pair_law` is called
only by `fluidfix selfcheck` (F9), so no guard run has ever consulted it.
Concretely, PARTITION becomes reachable at runtime on three observations the
body does not take today:

1. the FULL failing-test set (today `failing_output()` uses `-x` and sees one
   — F3);
2. a per-candidate failing COUNT (today `Oracle.check` returns
   `(bool, first-failure line)` — oracle.py:185 — so PARTIAL cannot be
   computed even though the full suite is already run for every candidate);
3. the site -> tests-repaired map, one subtraction away once (1) and (2)
   exist, and already half-present in the harvest log (F8).

## 5. Potential

- PARTITION actuated on this fixture turns an unconditional refusal into a
  green suite: measured (F7) pass 1 refuses in 2.9s with the tree untouched;
  the linear path costs one already-generated edit plus a 2.7s guard pass,
  3 suite runs, ending 5 passed / 0 failed.
- Cost of the quadratic answer PARTITION avoids, measured here: 18 single-edit
  runs = 3.5s, versus 153 naive pair combinations ~30s at the measured
  0.20s/run, of which the 80 cross-site pairs took a measured 15.7s to find
  exactly one green. Ratio ~8.5x on this fixture. The Box2D
  1,063-vs-564,453 ratio quoted in `docs/PAIR_LAW_PROMPT.md` is unmeasured by
  me.
- Cost of MEASURING the byte: the two bits that decide it (EXHAUSTED,
  DISJOINT) need zero extra suite runs — EXHAUSTED is "the search ended with
  no green and no budget stop", DISJOINT is derivable from the harvest log the
  body already writes (F8). A per-candidate failing count (for PARTIAL and a
  proper CANCELING check) also needs no extra run: the full suite already runs
  per candidate and only its summary line is discarded.
- How often real repositories present this two-bug shape: unmeasured.
- Whether a PARTITION path is safe when the groups are only nearly
  independent: unmeasured — this fixture's groups were verified disjoint by
  coverage and I built no near-miss.

## 6. Defects

D1 — OBSERVATION (in the body). The guard cannot see a second failing site.
`Oracle.failing_output()` runs pytest with `-x` (oracle.py:246), so the
last-failed cache holds one test; `build_packet`'s `--lf` coverage
(localize.py:137) then returns `anchor_lines=[]` for `inventory.py` (F3), so
no candidate is ever proposed there — even when the file is passed in
explicitly (measure.out STEP 3). Evidence: measure2.out STEP A.

D2 — WORDING. The refusal reads "fault is outside the taught vocabulary
(candidate files tried: billing.py). teach it once: docs/TEACHING.md". Both
faults are inside the shipped vocabulary; the true fix for one of them is
recorded in the same report as tried-and-rejected, killed by a test in
another module (F2). The advice given cannot help, and the situation actually
observed — a candidate that reduces the failure count, refuted by a test at a
disjoint site — is the PARTITION shape. `GuardReport.summary()` already
distinguishes three refusal causes (guard.py:57-105); this is a fourth it
does not have.

D3 — ACTUATION (absent, not wrong). `pair_law` has no call site in the body
(F9), so the PARTITION ruling this fixture's byte produces could not reach an
actuation even if the bits were measured; and there is no actuation to reach —
nothing in `acts.py`/`loop.py` can pin one group's repair and continue on the
residue, which is the operation F7 performed by hand.

NO RULING DEFECT FOUND. On the byte measured from the completed search
(23 = EXHAUSTED|PARTIAL|DISJOINT|CHEAP) the law ruled PARTITION, the correct
and cheapest answer for this program, and ruled it identically under all four
readings of the two bits no code owns (7 / 23 / 39 / 55). The engine law was
also right on the situation it was given (`REFUTED ->
HARVEST_COUNTEREXAMPLE`); that harvest is what carries the evidence for D1
and D2.

## 7. Verdict

On a genuine two-bug fixture the PAIR law rules PARTITION on the measured byte
23 (EXHAUSTED|PARTIAL|DISJOINT|CHEAP), and the linear path it names converts
the guard's refusal into a green suite in one extra 2.7s pass — every defect
found is in the body, which sees only the first failing test, computes none of
the eight bits, and then reports a vocabulary gap that does not exist.
