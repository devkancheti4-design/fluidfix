# 16-sight-exhaustive — REPORT

## 1. Target

All 256 inputs of the SIGHT law (`src/fluidfix/sight.py`) vs `docs/laws/sight.c`'s spec; R1/R2 checked algebraically lane by lane; UBIQUITOUS penalty behaviour on every input.

## 2. Method

Read, in full: `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/sight.py`, `/Users/kanchetidevieswar/neo/fluidfix/docs/laws/sight.c`, `/Users/kanchetidevieswar/neo/fluidfix/tests/test_sight_law.py`, the selfcheck section `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/cli.py:500-524`, the only body caller `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py:118-302` (`find_candidate_files`), its two call sites `guard.py:483` and `guard.py:536`, the C ranking `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/coracle.py:493-561`, and `CHANGELOG.md:270-290`.

Scripts written next to this report (all paths absolute, rerunnable):

| file | what it does |
|---|---|
| `exhaustive.py` | sections A-H: 256-input table, lane algebra, R1/R2 algebra, UBIQUITOUS on all 128 lower-byte pairs, body-constructible inputs, out-of-byte domain, test pins. Output: `exhaustive.out`, `table_256.txt` |
| `harness.c` | `#include`s the authored `sight.c` verbatim (its `main` renamed) and dumps `sight(x)` and the file-static `spec(x)` for all 256; built at `-O2` and under `-fsanitize=undefined`. Output: `c_table.txt`, `c_table_ubsan.txt` |
| `tiebreak_demo.py` | applies the caller's sort key, transcribed verbatim from `guard.py:195,300-301`, to two files the law puts in the same class. Output: `tiebreak_demo.out` |
| `tmo.sh` | `timeout(1)` does not exist on this macOS (`which timeout` -> not found); this is the perl-`alarm` equivalent used as `./tmo.sh 300 cmd ...` |

Runs, each under `nice -n 15 ./tmo.sh 300`, one at a time: `exhaustive.py`; `cc -O2 harness.c` + run; `cc -O1 -fsanitize=undefined harness.c` + run; `pytest tests/test_sight_law.py`; `fluidfix selfcheck` (`selfcheck.out`); `cc -O2 docs/laws/sight.c` + run as its author runs it (`sight_authored.out`); `tiebreak_demo.py`. No real-repo runs (target does not call for them). Nothing outside this directory was written; `git status --porcelain` shows only `?? research/`.

## 3. Findings

**F1. The Python port matches sight.c's specification on all 256 inputs; every output is in 0..7; priority 1 is never emitted.**
Command: `nice -n 15 ./tmo.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive.py` (section A)
```
mismatches vs spec_c            : 0  []
mismatches vs my closed form    : 0
outputs outside 0..7            : []
how many inputs land on each priority: {0: 224, 1: 0, 2: 8, 3: 12, 4: 6, 5: 3, 6: 2, 7: 1}
```
Full table: `table_256.txt` (x, bits, sight, spec, closed form).

**F2. The Python port is identical to the compiled authored C kernel on all 256 inputs, and the kernel has no undefined behaviour on any byte input.**
Command: `cc -O2 -o sight_table harness.c && ./sight_table > c_table.txt`, then a Python dump of the port to `py_table.txt` in the same format, then `diff c_table.txt py_table.txt`; then `cc -O1 -fsanitize=undefined -fno-sanitize-recover=all -o sight_table_ubsan harness.c && ./sight_table_ubsan`.
```
== diff C kernel/spec vs Python port (empty = identical on all 256) ==
IDENTICAL: 256 lines
     256 c_table.txt
== build -O1 -fsanitize=undefined ==
ubsan exit=0
C kernel: non-pointing inputs where UBIQ != +1: 0
UBSAN TABLE IDENTICAL TO -O2 TABLE
```
(`c_table.txt` has three columns: x, C `sight(x)`, C `spec(x)`; all three agree with the Python row for row.)

**F3. Lane algebra: each authored lane reduces to exactly one bit of x, so the whole law has the closed form `0 if x&7 else ctz(((x>>1)&0x3C)|64) + bit7`.**
Command: `exhaustive.py` section B.
```
  OK   _POINT1(x)   == (x & 7 != 0)
  OK   _FAILONLY(x) == 4  * bit3
  OK   _NAMED(x)    == 8  * bit4
  OK   _TOUCHED(x)  == 16 * bit5
  OK   _SMALL(x)    == 32 * bit6
  OK   _UBIQ(x)     == bit7
  OK   circ sum     == (x>>1) & 0x3C (disjoint powers of two, sum == OR)
  OK   _EMIT(m)     == lowest set bit, m in 1..255
  OK   _POINT1 identity on -65536..65535 (signed, Python port)
  OK   mask == 65 on pointing inputs, == circ|64 on non-pointing
```
Notes: `_SMALL` is `(63 & y) - (31 & y)` with `y = x>>1`, which is bit 5 of `y`, i.e. bit 6 of `x` — the odd-looking authored expression is a single-bit projection. The docstring's derivation of POINT1 (`-high + high + (low != 0)`) holds on the signed range checked, not only on the byte.

**F4. R1 holds algebraically: the pointing tier lands on mask bit 0 (ctz 0) and the lowest circumstantial slot is mask bit 2 (ctz >= 2); the gap is the reserved priority 1. Exhaustively: 0 violations in 7,168 pairs.**
Command: `exhaustive.py` section C.
```
pointing inputs: 224   non-pointing inputs: 32
max sight over pointing     : 0
min sight over non-pointing : 2
R1 pairs checked: 7168   violations: 0
```

**F5. R2 holds algebraically: `gate = POINT1 - 1` is 0 on every one of the 224 pointing inputs and -1 (all ones) on every one of the 32 non-pointing inputs; both the circumstantial sum and the penalty are ANDed with it. Converse also holds: on non-pointing inputs the penalty is never lost.**
Command: `exhaustive.py` section D.
```
gate values on pointing inputs    : {0}   (0 kills circ AND penalty)
gate values on non-pointing inputs: {-1}   (-1 = all ones passes both)
R2 pointing inputs checked: 224   violations: 0
converse: non-pointing inputs where UBIQ does NOT add exactly 1: []
```

**F6. UBIQUITOUS on every input: over the 128 (x, x|128) pairs the penalty is +1 on exactly the 16 non-pointing lower bytes and 0 on the 112 pointing ones. It demotes by exactly one class, creates cross-class ties, and never inverts the order of two non-pointing files.**
Command: `exhaustive.py` section E.
```
delta histogram over the 128 pairs: {1: 16, 0: 112}
   low bits                                w/o with
     0 -                                     6    7
     8 FAILONLY                              2    3
    16 NAMED                                 3    4
    32 TOUCHED                               4    5
    64 SMALL                                 5    6
   (12 more rows in exhaustive.out; every FAILONLY row is 2 -> 3)
cross-tier ties the penalty creates (a|UBIQ ties b, a != b, both non-pointing):
  43 ordered pairs; distinct (prio(a), prio(a|UBIQ)==prio(b)) classes: [(2, 3, 3), (3, 4, 4), (4, 5, 5), (5, 6, 6)]
    FAILONLY+UBIQUITOUS -> 3  ==  NAMED -> 3
    NAMED+UBIQUITOUS -> 4  ==  TOUCHED -> 4
    TOUCHED+UBIQUITOUS -> 5  ==  SMALL -> 5
    SMALL+UBIQUITOUS -> 6  ==  - -> 6
order flips: ... 0 ordered pairs (a, b)
```
Why 0 flips: a flip needs `prio(a) < prio(b)` and `prio(a)+1 > prio(b)`, impossible for integers. So the penalty can only hand a decision to the caller's tie-break (see F9), never reverse the law's own order. This is the spec's intent (`base + ((x >> 7) & 1)`), stated here so nobody reads the ties as a bug.

**F7. 64 of the 256 inputs are contradictory for the body's only caller: FAILONLY (`specificity >= 0.9`) and UBIQUITOUS (`specificity < 0.25`) are measured from the same variable. Of the 64, 56 are pointing (rule 0 anyway) and 8 are the only inputs that reach priority 3 through the penalty; in the body priority 3 is reachable only through NAMED.**
Command: `sed -n 274,283p /Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` and `exhaustive.py` section F.
```
            failonly=specificity >= 0.9,
            ...
            ubiquitous=specificity < 0.25,
```
```
inputs with FAILONLY and UBIQUITOUS both set : 64 of 256
  of which pointing (rule 0 regardless)      : 56
  of which non-pointing                      : 8  -> rulings [3]
inputs constructible w.r.t. this constraint  : 192
priority 3 is emitted for 12 inputs; body-constructible: 4
  constructible priority-3 inputs: [(16, 'NAMED'), (48, 'NAMED+TOUCHED'), (80, 'NAMED+SMALL'), (112, 'NAMED+TOUCHED+SMALL')]
  priority 0: 224 inputs, 168 body-constructible
  priority 2:   8 inputs,   8 body-constructible
  priority 3:  12 inputs,   4 body-constructible
  priority 4:   6 inputs,   6 body-constructible
  priority 5:   3 inputs,   3 body-constructible
  priority 6:   2 inputs,   2 body-constructible
  priority 7:   1 inputs,   1 body-constructible
```
The law rules on them anyway (consistently: 3), and the tests pin them; they are simply situations the measurement cannot produce. Consequence: the cross-class tie `FAILONLY+UBIQUITOUS == NAMED` from F6 never happens in practice.

**F8. The body consults the SIGHT law on exactly one path: the Python guard, and only when the failing output names no in-repo, non-test `.py` file. When frames exist, `find_candidate_files` returns before the law is imported. The C and Java rankings never import it.**
Command: `sed -n 145,150p /Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` and `grep -rn "from .sight\|import sight\|fluidfix.sight" src/ tests/ | grep -v "^src/fluidfix/sight.py"`.
```
145:    ordered.reverse()
146:    if ordered:
147:        if evidence is not None:
148:            evidence["pointed"] = list(ordered[:limit])
149:            evidence["lanes"] = {"FRAMED": list(ordered[:limit])}
150:        return ordered[:limit]
```
```
src/fluidfix/cli.py:501:    from .sight import sight as _sight
src/fluidfix/guard.py:216:    from .sight import observe_bits as _sight_bits, sight as _sight
tests/test_sight_law.py:11:from fluidfix.sight import BITS, observe_bits, sight, situation
```
`grep -n "_sight\|sight(" src/fluidfix/coracle.py src/fluidfix/javaoracle.py` returns nothing. `coracle.py:497-498` says "Same lane the SIGHT law reads, resolved here" — it re-implements the NAMED idea by hand (frames, then stem scoring, then file size, `coracle.py:503-561`); the law itself is not called for Box2D or cglm.

A consequence for the FRAMED lane in the branch that does reach the law: `framed_files` (`guard.py:218-219`) is the set of basenames of every `.py` mention in the output, but this branch is only entered when every such mention failed the in-repo / is-file / not-test filters of `guard.py:132-140`. So on the law's path FRAMED can only fire by basename coincidence (a `tests/utils.py` frame and a `pkg/utils.py` source, or an unresolvable relative path). How often that happens: unmeasured.

**F9. Inside one priority class the caller breaks ties by AFFINITY first (the same filename-token overlap that sets NAMED), then specificity, then executed lines; the law's docstring and the caller's own comment say specificity first.**
Command: `grep -n "specificity, then executed-line\|Specificity still breaks ties\|ranked2.append((affinity\|ranked2.sort\|-t\[0\], -t\[1\]" src/fluidfix/sight.py src/fluidfix/guard.py` and `nice -n 15 ./tmo.sh 300 .venv/bin/python tiebreak_demo.py`.
```
sight.py:61:    When they point at different files the CALLER breaks the tie (this
sight.py:62:    module's callers use specificity, then executed-line count).
guard.py:208:    # Specificity still breaks ties INSIDE a priority class, never over it —
guard.py:195:        ranked2.append((affinity, specificity, n_fail, rel))
guard.py:300:    ranked2.sort(key=lambda t: (file_priority2(t[3], t[1], t[2]),
guard.py:301:                                -t[0], -t[1], -t[2], t[3]))
```
```
  pkg/types.py               bits=74  sight=0  affinity=0.0 specificity=1.0 n_fail=40
  pkg/shell_completion.py    bits=20  sight=0  affinity=1.0 specificity=0.3 n_fail=500
order under the key AS WRITTEN (guard.py:300-301, affinity first):
    pkg/shell_completion.py
    pkg/types.py
order under the key AS DOCUMENTED (sight.py:61-62, specificity first):
    pkg/types.py
    pkg/shell_completion.py
```
The law's ruling is untouched (both files are 0; R1/R2 are not involved). The pair in the demo is synthetic; whether this tie-break has ever changed which pointed-at file was opened first on a real repo is unmeasured.

**F10. The project's own three verifications pass today.**
Commands: `nice -n 15 ./tmo.sh 300 .venv/bin/python -m pytest tests/test_sight_law.py -q -p no:cacheprovider`; `nice -n 15 ./tmo.sh 300 .venv/bin/fluidfix selfcheck`; `nice -n 15 ./tmo.sh 300 cc -O2 -o sight_authored docs/laws/sight.c && ./sight_authored`.
```
13 passed in 0.03s
```
```
sight law vs specification, all 256:         256/256
sight law tiers (R1 pointing > circumstantial,
  R2 no penalty on pointing, R3 monotone):    all hold
SELFCHECK PASS — 6 laws re-derived
```
```
  specification, all 256 inputs        0 wrong
  R1  pointing outranks non-pointing    0 violations
  R2  UBIQUITOUS never demotes pointing  0 violations
  R3  monotone in the evidence bits      0 violations
  the three incidents                    0 violations
  evidence-free files span              2 classes (UBIQ splits 6/7)
  1.24 ns per candidate file  (sink 440000000)
  TOTAL  256 inputs  0 violations
```
(CHANGELOG records 1.22 ns; this machine measured 1.24 ns.)

**F11. Domain note, not a defect: outside the byte the penalty term is `x >> 7`, so an over-wide input leaves 0..7. Neither packer can produce one.**
Command: `exhaustive.py` section G.
```
  sight(  256) =    8   (x>>7 = 2)
  sight( 1024) =   14   (x>>7 = 8)
  sight(   -1) =    0   (x>>7 = -1)
  max packable by situation(): 255
  observe_bits(all True)     : 255
```
`observe_bits` rejects unknown lanes (`test_observe_bits_rejects_an_unmeasured_lane`), and the body builds the byte only through it (`guard.py:280`). C behaviour beyond the byte: unmeasured (the UBSan run covered 0..255 only).

**F12. Test pinning: 9 inputs are pinned by a named assertion; all 256 are pinned by the loop test against `spec()`.**
Command: `exhaustive.py` section H.
```
    0 -  -> 6 | 1 FRAMED -> 0 | 2 SCARCE -> 0 | 4 LITERAL -> 0 | 16 NAMED -> 3
  112 NAMED+TOUCHED+SMALL -> 3 | 128 UBIQUITOUS -> 7 | 130 SCARCE+UBIQUITOUS -> 0 | 144 NAMED+UBIQUITOUS -> 4
  9 inputs pinned by name; the other 247 only by the exhaustive loop test_matches_specification_on_all_256_situations (which pins all 256)
```
No input is unpinned; the spec transcription in the test is the same function as sight.c's `spec()`, and F2 ties both to the compiled kernel.

## 4. Lanes

Reached by this work (analysis, not repair runs): every one of the 256 inputs and every emitted priority {0, 2, 3, 4, 5, 6, 7}; both tiers; the penalty on all 128 pairs; the compiled C kernel on all 256.

Reached by the body today (from reading `guard.py`, F7/F8): on the Python path with no in-repo source frame — priority 0 via SCARCE or LITERAL (FRAMED only by basename coincidence), 2 via FAILONLY, 3 via NAMED, 4 via TOUCHED, 5 via SMALL, 6 via nothing, and 7 / 4 / 5 / 6 via the penalty on nothing / NAMED / TOUCHED / SMALL.

Never reached by the body, and why:
- priority 1 — by design; the spec steps 0 -> 2.
- FAILONLY+UBIQUITOUS (64 inputs, 8 non-pointing) — contradictory for the caller, both bits come from one `specificity`. No observation makes these reachable without measuring the two bits from different quantities; that would be a different law.
- FRAMED together with a real traceback frame — the body returns at `guard.py:150` before the law; the law is never asked. Reachable by an actuation change (pass the framed list through `file_priority2` instead of returning), not by a new observation.
- any lane at all on C (Box2D, cglm) or Java repos — `coracle.py` and `javaoracle.py` never import the law. Reachable only by an actuation (a caller); the C path already measures the quantities it would need for NAMED, SMALL-by-size and, with gcov, FAILONLY/UBIQUITOUS.

## 5. Potential

- Passing the frames case through the law: today a SCARCE- or LITERAL-pointed file that is not in the traceback is not a candidate at all (`return ordered[:limit]`, limit 3 at `guard.py:483`), while the law would put it at priority 0 beside the framed files. Value on real repos: unmeasured.
- Consulting the law on the C path: unmeasured here; targets 17 and 19 measure file ranking on Box2D/cglm directly.
- Fixing the tie-break to match its documentation (specificity before affinity): changes order only inside a priority class; the demo pair flips, real-repo frequency unmeasured.
- The FAILONLY+UBIQUITOUS lane: worth nothing — contradictory by construction (F7).
- The penalty itself: measured to be exactly one class on the 16 lower bytes it touches and to never invert an order (F6); nothing to add.

## 6. Defects

- **Ruling: none found.** 0/256 mismatches vs spec, 0/256 vs the compiled kernel, R1 0/7168, R2 0/224, R3 0 (F1, F2, F4, F5, F10).
- **Wording: one.** `sight.py:61-62` and `guard.py:208-209` say the caller separates equal-rank files by specificity then executed lines; the code (`guard.py:195, 300-301`) sorts by affinity first. Evidence: F9, `tiebreak_demo.out`. The docstring is what a reader of the law is told; it should say affinity, specificity, executed lines, path — or the key should be what it says.
- **Actuation: one gap, no wrong outcome shown.** The law is bypassed when any in-repo source frame exists (`guard.py:146-150`) and is not called at all for C/Java (F8). Nothing here is a ruling the law made and the body ignored; it is a ruling the body never requested. Whether it has cost a repair: unmeasured.
- **Observation: one note.** On the only path that reaches the law, FRAMED is measured by basename against mentions that the same function already rejected as non-source (F8, `guard.py:132-140` vs `218-219`). No misclassification demonstrated; frequency unmeasured.

## 7. Verdict

The SIGHT law's Python port equals the authored C kernel and its spec on all 256 inputs, R1 and R2 hold by the gate algebra on every input (gate is 0 on all 224 pointing inputs, -1 on all 32 others), and UBIQUITOUS is exactly +1 on the 16 non-pointing lower bytes and 0 on the 112 pointing ones with no order inversion; no ruling defect — but the body asks the law only on the Python no-frames path, cannot construct the 64 FAILONLY+UBIQUITOUS inputs, and misdescribes its own tie-break (affinity first, not specificity).
