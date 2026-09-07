# 24-pair-canceling-fixture

## 1. Target
Build the compensating-repair shape (a sign flip plus a candidate that breaks an
operator so the faults cancel), compute CANCELING from single-edit results, and
confirm the veto.

## 2. Method

Read: `src/fluidfix/pair.py` (the law and its docstring specification),
`docs/PAIR_LAW_PROMPT.md` (the authoring prompt, incidents 1-5),
`tests/test_pair_law.py`, `src/fluidfix/cli.py:525-565` (the selfcheck
re-derivation), `src/fluidfix/loop.py` (the single-edit search and the
engine-law AMB ruling), `src/fluidfix/acts.py` (act vocabulary),
`src/fluidfix/oracle.py`, `src/fluidfix/localize.py`.

Built four fixtures, all inside this directory, all Python, all judged by their
own pytest suite through fluidfix's own `Oracle`:

| fixture | shape |
|---|---|
| `fixtures/A_unity/` | the recorded Unity incident: ONE sign flip in `project_on_plane`; `Vec3.__add__` breakable in one edit; nothing pins vector addition |
| `fixtures/C_canceling/` | the same math with TWO defects in `project_on_plane` (`dot(v,n) + 1` and the sign), so no single edit is green; both an honest pair and a compensating pair exist |
| `fixtures/D_partition_plus_canceling/` | C plus one independent single-edit defect (`count_above` strictness) and its own failing test |
| `fixtures/E_only_canceling/` | C with the honest sign fix written `v+scale(n, d)` — outside kind 3's `\s[-+]\s` signal — so the ONLY reachable jointly-green pair is the compensating one |

Scripts kept here, all re-runnable:

- `nt.sh SECS CMD...` — nice+timeout wrapper (macOS has no coreutils `timeout`;
  `nice -n 15 perl -e 'alarm shift; exec @ARGV'`).
- `pair_probe.py FIXTURE` — report-only. Uses fluidfix's own `build_packet`,
  `MechanicalObserver`, `lanes` EMIT/ADVANCE/HALT, `act_for`, `candidates` and
  `Oracle` to run a complete single-edit search, records each candidate's
  FAILING TEST SET, then enumerates every distinct-line candidate pair and runs
  the suite on it — because `pair.py` is never called by the body, the pair
  half had to be built here. It then computes the observation byte and calls
  `pair_law`. Outputs: `probe_A.out`, `probe_C.out`, `probe_D.out`, `probe_E.out`.
- `body_run.py FIXTURE` — what fluidfix actually does today (real `repair()`).
  Outputs: `body_A.out`, `body_E.out`.
- `veto_reach.py` — exhaustive 256-input counterfactual for the veto plus the
  engine law's ruling on fixture E's pair. Output: `veto_reach.out`.

Every run: `./nt.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python ...`,
one at a time. Nothing outside this directory was written; no git state changed.
`work/` (the scratch copies) was deleted after the runs; the probe recreates it.

## 3. Findings

### F1. The compensating-repair shape reproduces exactly, and the engine law's AMB lane is what stops it
`./nt.sh 300 .../python body_run.py fixtures/A_unity` (`body_A.out`):

```
repaired=False refused=True ambiguous=True
suite_runs=8 acts_tried=[6, 6, 7, 8, 6, 7, 6, 7, 7, 8] seconds=2.9
greens=['        return Vec3(*[a - b for a, b in zip(self.c, o.c)])', '    return v - scale(n, d)']
reason: AMBIGUOUS: 2 candidates at 2 different lines (14, 36) all pass the suite ...
         (engine law: BUILT+AMB -> ADD_STATE, never guess)
file restored byte-exactly: True
```
Line 36 is the real fix; line 14 breaks `Vec3.__add__` so the two faults cancel.
This is the docs' incident, in Python, in 2.9s.

### F2. Measured per its own definition, CANCELING is FALSE on the Unity shape
`./nt.sh 300 .../python pair_probe.py fixtures/A_unity` (`probe_A.out`):

```
  [ 3] line  14 kind  3 GREEN fail=0 | return Vec3(*[a - b for a, b in zip(self.c, o.c)])
  [ 9] line  36 kind  3 GREEN fail=0 | return v - scale(n, d)
  PAIR GREEN [1,9] ... | PAIR GREEN [3,4] ... | PAIR GREEN [3,9] ... | PAIR GREEN [4,9] ...
pair suite runs: 40; jointly green: 4
  EXHAUSTED  False
  CANCELING  False
  CHEAP=1 TAUGHT=1  byte= 56 -> SINGLE    | without CANCELING: byte= 56 -> SINGLE
```
The bit is defined as "a pair is green JOINTLY while each member alone leaves
the suite red AND reduces nothing". Every one of the four jointly-green pairs
here contains a member that is green ALONE, so no pair qualifies. The law rules
SINGLE ("a single edit has not been exhausted; keep going") — correct, and the
requirement "never reaches a pair search" is delivered by R1 (the EXHAUSTED
gate), not by the veto. `tests/test_pair_law.py::test_incident_unity_...`
encodes this incident as `PAR|COU|CHE|TAU|CAN` (byte 122); that byte is
hand-assigned, and the bit's own definition does not produce it from a faithful
replica of the incident. Both encodings rule "no pair search", so no ruling is
wrong — the mismatch is in the wording/encoding of the incident.

### F3. An exhausted single-edit search with a real compensating pair: CANCELING measured TRUE, veto confirmed
`./nt.sh 300 .../python pair_probe.py fixtures/C_canceling` (`probe_C.out`):

```
baseline failing tests (1): ['test_vec.py::test_project_removes_the_normal_component']
single-edit candidates: 12          (all 12 red — see probe_C.out lines 5-16)
  PAIR GREEN [3,8] lines 19+40 | return Vec3(*[a - b ... || d = dot(v, n) | hidden property VIOLATED
  PAIR GREEN [8,11] lines 40+41 | d = dot(v, n) || return v - scale(n, d) | hidden property holds
pair suite runs: 60; jointly green: 2
  EXHAUSTED  True
  PARTIAL    False
  CANCELING  True
  CHEAP=1 TAUGHT=1  byte=121 -> REFUSE    | without CANCELING: byte= 57 -> REFUSE
```
`[3,8]` is the compensating pair (drop the spurious term AND break `__add__`);
`[8,11]` is the honest repair. The "hidden property" is a check the suite does
NOT contain (`Vec3(1,2,3)+Vec3(4,5,6) == Vec3(5,7,9)` and a second projection);
it is used only to label a green pair honest or corrupting, never by any law.
`pair_law(121) = 7 = REFUSE`. **The veto holds on a measured byte.**

### F4. The veto is the ONLY thing between an actuated pair search and shipping a corruption
`probe_E.out` — fixture E, the honest sign fix removed from the vocabulary:

```
single-edit candidates: 10          (all red)
  PAIR GREEN [3,8] lines 19+40 | return Vec3(*[a - b ... || d = dot(v, n) | hidden property VIOLATED
pair suite runs: 40; jointly green: 1
  EXHAUSTED True   PARTIAL False   CANCELING True
  CHEAP=1 TAUGHT=1  byte=121 -> REFUSE
```
Exactly ONE jointly-green pair exists and it corrupts vector addition globally.
One green at one site is not ambiguous, so the engine law would not save it
(`veto_reach.out`):
```
   decide(BUILT=1, AMB=0) = SHIP
   decide(BUILT=1, AMB=1) = ADD_STATE   (fixture A and C: two greens at two sites)
```
The body's own single-edit run on E refuses honestly today (`body_E.out`):
`reason: every candidate left the suite red — fault is outside this vocabulary
or the observations are wrong`.

### F5. CANCELING cannot distinguish two bugs that cancel from one fault needing two edits
In fixture C both jointly-green pairs satisfy the bit's definition verbatim
(both members red alone, neither reducing): `[3,8]` corrupts, `[8,11]` is the
correct repair (`probe_C.out`, `hidden property holds`). So the veto that
refuses the compensating pair refuses the honest two-edit repair with it. The
prompt's R3 says "Two bugs that cancel satisfy exactly this description; so
does nothing else we have measured" — `[8,11]` is a measured counterexample to
that clause. The ruling (REFUSE) is a conservative refusal, not a wrong repair.

### F6. Exhaustive counterfactual: what the veto actually changes
`./nt.sh 120 .../python veto_reach.py` (`veto_reach.out`):
```
   inputs with CANCELING set:            128
   ...where the veto CHANGES the ruling: 126
   ...where it changes nothing:          2 (already REFUSE without it)
     CAPPED 64 | SINGLE 32 | PARTITION 16 | TEACH 5 | WIDEN 4 | BUDGET 3 | PAIR 2
   inputs where the veto overrules an actual PAIR: 2 -> bytes [91, 123]
```
On the four bytes I could MEASURE from fixtures (56, 121, 57, 121) the veto is
confirmed but inert: byte 121 rules REFUSE with or without CANCELING, because
PARTIAL is false and the law was already refusing (`veto_reach.out` section 2).
The veto is decisive only on bytes 91 and 123 (= 27 and 59 plus CANCELING),
which require PARTIAL. See section 4 for why I could not construct that byte.

### F7. Counting failing tests is not enough to measure PARTIAL (a trap I fell into and fixed)
First run of `pair_probe.py fixtures/D_partition_plus_canceling` scored 4 of 12
candidates `REDUCES` and reported `PARTIAL True`; all four were candidates that
break module collection (`class Vec3` -> `class Vec2`), which pytest reports as
one ERROR line — fewer "failures", zero progress. With PARTIAL redefined as a
PROPER SUBSET of the baseline failing set (`pair_probe.py`, the `e["reduces"]`
comment), the re-run gives (`probe_D.out`):
```
  [ 0] line  14 kind  1 red   fail=1 | class Vec2:
  ...
  EXHAUSTED  True   PARTIAL    False   CANCELING  False
  pair suite runs: 60; jointly green: 0
```

### F8. DISJOINT's evidence is not in the packet the body builds today
Fixture D has an independent second defect at line 47 (`if x >= t:`) with its
own failing test, but the packet built from the first failing test does not
contain it:
```
$ ./nt.sh 120 .../python -c "... build_packet(o,'vec.py',coverage_target='vec') ..."
packet lines: [14, 15, 16, 18, 19, 21, 24, 25, 27, 28, 31, 32, 35, 36, 39, 40, 41, 44]
```
Line 44 (`def count_above`) is present, lines 45-49 are not — `failing_output()`
runs `-x`, so only the first failing test's traceback and coverage are seen. No
candidate that repairs the second failing test was ever generated, so neither
DISJOINT nor PARTIAL could be measured, in a fixture built to have both.

### F9. `pair_law` is not called by the body at all
```
$ grep -rn "pair_law\|from .pair\|import pair" src/
src/fluidfix/cli.py:527:    from .pair import pair_law as _pair
src/fluidfix/pair.py:...
```
The only caller is `cli.py`'s `selfcheck`. `loop.py` never asks the PAIR law
anything; every byte in this report was computed by `pair_probe.py`.
Baseline for the record: `tests/test_pair_law.py` = `16 passed in 0.02s`;
`fluidfix selfcheck` prints `pair law vs specification, all 256: 256/256`,
`R1/R2/R3 all hold`, `situations that reach a PAIR search: 2/256`,
`SELFCHECK PASS — 6 laws re-derived`.

## 4. Lanes

Reached from a measured fixture:
- **REFUSE (7)** — fixtures C and E, byte 121, via the CANCELING veto. This is
  the target's "confirm the veto", confirmed.
- **SINGLE (6)** — fixture A, byte 56 (EXHAUSTED false).
- **TEACH (3)** / **BUDGET (4)** — reached only as counterfactuals of the same
  fixtures with CANCELING cleared or TAUGHT/CHEAP set differently (bytes 9, 25,
  41 in `probe_C.out`/`probe_D.out`); TAUGHT and CHEAP are not measured by any
  code, so which of these a real run would land on is **unmeasured**.

Never reached:
- **PARTITION (0)** — needs DISJOINT: two failing tests whose repair sites are
  disjoint AND both sites observed. F8 shows today's packet cannot supply that
  from one `build_packet` call; a packet per failing test would.
- **PAIR (1)** — needs `EXHAUSTED+PARTIAL+COUPLED+CHEAP` and not CANCELING
  (bytes 27, 59). I could not construct PARTIAL together with a canceling pair:
  by the bit's own definition a canceling pair's members may not reduce the
  failing count, so PARTIAL has to come from a THIRD candidate that reduces
  without greening, while the pair still greens the WHOLE suite — i.e. a failing
  test repaired both by that third candidate and by the pair. Whether such a
  program exists is **unmeasured**; I did not build one.
- **WIDEN (2)** — needs PARTIAL with COUPLED false; same missing observation.
- **CAPPED (5)** — needs a budget; the probe gave none.

## 5. Potential

- What the veto is worth, measured: fixture E has exactly **1 of 1** jointly-green
  pairs corrupting (the hidden property fails), and it is uniquely green, so the
  engine law rules **SHIP** on it (`veto_reach.out`). Fixture C has **1 of 2**
  jointly-green pairs corrupting; there the engine law's AMB lane would also
  catch it (two greens, two site-pairs). So on the two fixtures where a pair
  search would find something, the CANCELING veto is the only protection in one
  of them and redundant with AMB in the other.
- What the veto costs, measured: in fixture C the veto refuses the honest
  two-edit repair `[8,11]` along with the compensating one (F5). Today that
  costs nothing, because no pair search exists to refuse.
- Pair-search cost on these fixtures, measured: 10-12 single-edit candidates
  produced 40-60 distinct-line pair suite runs (`probe_*.out`, `pair suite
  runs:`), a 4-5x multiplier at toy scale. The Box2D figures (1,063 candidates,
  564,453 pairs) are quoted from `docs/PAIR_LAW_PROMPT.md`; I did not re-measure
  them — **unmeasured** here.
- The cheapest missing observation is not CANCELING but the pair run itself:
  the half of CANCELING that says "each member alone is red and reduces
  nothing" is computable from a completed single-edit search (my probe computes
  it from `fail` sets), but "green JOINTLY" requires running pairs — the very
  thing the law is deciding whether to start. Any body that sets this bit
  honestly must already have run some pairs; a body that sets it from the
  measurable half alone would set it on almost every rejected pair. Fixture C:
  **all 60** distinct-line pairs have both members red and non-reducing, of
  which **2** are jointly green.

## 6. Defects

- **Wording (F2).** The Unity incident is encoded in `tests/test_pair_law.py`
  and `docs/PAIR_LAW_PROMPT.md` as CANCELING=1, but a faithful replica of that
  incident measures CANCELING=0 under the bit's own definition, because each
  member of the compensating pair is green ALONE. No ruling is wrong (both bytes
  rule "no pair search"; R1 does the work), but the incident does not exercise
  the veto it is cited for.
- **Wording (F5).** "Two bugs that cancel satisfy exactly this description; so
  does nothing else we have measured" (`docs/PAIR_LAW_PROMPT.md`, R3) is
  refuted by a measured counterexample: fixture C's honest two-edit repair
  satisfies the description verbatim. The ruling on that byte is a conservative
  refusal, not a wrong repair.
- **Observation (F8).** DISJOINT and PARTIAL cannot be measured from the
  packet the body builds today: `failing_output()` uses `-x`, so only the first
  failing test's site is ever observed. This is what keeps PARTITION and PAIR
  unreachable, not the law.
- **Observation (F7).** Any future PARTIAL measurement must use a proper-subset
  test, not a count: a candidate that breaks collection reduces the count while
  breaking everything. Measured: 4 of 12 candidates in fixture D looked like
  progress under counting and none do under subsets.
- **Ruling:** none found. On every byte I measured (56, 121, 57), `pair_law`
  agreed with the transcribed specification and with `selfcheck` (256/256).

## 7. Verdict
The compensating-repair shape reproduces in Python and the CANCELING veto holds
exactly as authored (byte 121 -> REFUSE, and fixture E shows it is the only
thing that would stop an actuated pair search from shipping a suite-green
corruption the engine law would rule SHIP) — but the bit as defined also fires
on an honest two-edit repair, does not fire on the Unity incident it was
authored from, and cannot be measured at all without running pairs, while
PARTIAL/DISJOINT — the bits that would make the veto decisive rather than
redundant — are not observable from the packet the body builds today.
