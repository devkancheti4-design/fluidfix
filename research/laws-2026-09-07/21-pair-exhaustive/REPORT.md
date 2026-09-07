# 21-pair-exhaustive — REPORT
(Relayed by the coordinator: the agent's own write of this file was blocked by a
harness rule. Scripts and raw outputs in this directory are the agent's own and
are rerunnable: exhaustive.py, props.py, domain.py, c_vs_py.sh, run.sh,
exhaustive_output.txt, props_output.txt, domain_output.txt, c_outputs.txt.)

## 1. Target
All 256 inputs of pair_law vs the authored specification, R1-R5, and the five
incidents in docs/PAIR_LAW_PROMPT.md; plus inputs no test pins independently of
the authored case table.

## 2. Method
Read in full: src/fluidfix/pair.py, docs/laws/pair.c, docs/PAIR_LAW_PROMPT.md,
tests/test_pair_law.py, src/fluidfix/cli.py:526-565, CHANGELOG.md 0.14.0.
Wrote and ran, all inside the agent directory: exhaustive.py (three independent
models over 256 inputs, R1-R5, incidents, act distribution, pin census, full
table), props.py (bit relevance, single-bit escalation, R2 scope, contradictory
region, cost recomputation), domain.py (totality probe), c_vs_py.sh (compiles
docs/laws/pair.c and compares C to the port on all 256 inputs; runs the authored
self-check unmodified). NOTE: this machine has no coreutils timeout
(`which timeout gtimeout` -> not found); run.sh supplies the same contract via
nice -n 15 plus a hard 300s alarm kill. One run at a time. No repo state changed.

## 3. Findings

F1 - Kernel matches the authored specification AND an independent algebraic
re-derivation on all 256.
    A kernel vs B authored case table : 0 disagreements []
    A kernel vs C algebraic re-deriv. : 0 disagreements []
    B case table vs C re-derivation   : 0 disagreements []
    mask is never zero (ctz terminates): min mask = 128
Model C is built from lane closed forms each verified over 256 inputs first
(TOTAL lane disagreements: 0): READY=EXHAUSTED, BLOCK=CANCELING|CAPPED,
CHEAP2=2*CHEAP, NOTCOUP=4*!COUPLED, TEACH=8*!TAUGHT, BUDGET=16*!CHEAP,
CAPPED_L=32*CAPPED, SINGLE=64*!EXHAUSTED. The mask is a one-hot-per-lane weight
sum plus floor 128; priority is its lowest set bit.
CAVEAT STATED BY THE AGENT: B and C are two routes to the same authored formula.
The "specification" is the author's own case table, appearing three times
(docs/laws/pair.c:spec, tests/test_pair_law.py:spec, src/fluidfix/cli.py:_pspec)
- exhaustive self-consistency, not an independent oracle for intent.

F2 - The Python port is behaviourally identical to the authored C over the whole
documented domain.
    C kernel vs Python port, all 256 inputs: 0 disagreements []
    --- authored self-check (docs/laws/pair.c, unmodified) ---
      specification, all 256 inputs          0 wrong
      R1  no pair before EXHAUSTED           0 violations
      R2  DISJOINT outranks a pair           0 violations
      R3  CANCELING always ranks last        0 violations
      R4  PAIR requires PARTIAL progress     0 violations
      R5  PAIR never starts without CHEAP    0 violations
      the five incidents                     0 violations
      inputs that reach a PAIR search        2 of 256
      2.40 ns per decision
One structural difference: __builtin_ctz replaced by a `while low >> 1` loop.
Over 0..255 they agree exactly (see F9 outside the domain).

F3 - R1-R5 hold on all 256; the five incidents all rule as required.
    1 Unity ProjectOnPlane   byte 122 -> REFUSE    required REFUSE    OK
    2 Box2D contact_solver.c byte  33 -> BUDGET    required BUDGET    OK
    3 genuine two-bug        byte  55 -> PARTITION required PARTITION OK
    4 two coupled taught     byte  59 -> PAIR      required PAIR      OK
    5 nothing observed       byte   0 -> SINGLE    required SINGLE    OK
    pytest tests/test_pair_law.py -q -> 16 passed in 0.02s
    fluidfix selfcheck -> 256/256, all hold, 2/256 reach PAIR, 6 laws re-derived

F4 (TOP FINDING) - 108 of 256 inputs are pinned ONLY by the transcribed case
table; the whole CAPPED act and the whole WIDEN and TEACH lanes are among them.
    inputs with an EXACT act pinned independently of the spec table: 148/256
    inputs pinned ONLY by the transcribed spec table                : 108/256
       WIDEN        4: [3, 19, 35, 51]
       TEACH        5: [1, 9, 11, 17, 25]
       BUDGET       2: [41, 43]
       CAPPED      64: [128 ... 191]
       SINGLE      31: [2, 4, 6, ... 62]
       REFUSE       2: [49, 57]
    unpinned acts : ['WIDEN', 'TEACH', 'CAPPED']
"Pinned independently" = an assertion in tests/test_pair_law.py fixing an exact
act without consulting spec(). All 256 are covered by
test_matches_specification_on_all_256_situations, but that test and its table are
the same author's artefact, so those 108 rulings are asserted, not cross-checked.
Weakest: CAPPED - all 64 inputs rest on the table alone.

F5 - The PAIR lane sits exactly ONE unmeasured bit away from a REFUSE.
    single-bit jumps from REFUSE straight to an acting lane: 3
       x=49 EXHAUSTED|CHEAP|TAUGHT           + DISJOINT -> PARTITION
       x=57 EXHAUSTED|COUPLED|CHEAP|TAUGHT   + PARTIAL  -> PAIR
       x=57 EXHAUSTED|COUPLED|CHEAP|TAUGHT   + DISJOINT -> PARTITION
x=57 refuses; setting PARTIAL alone launches the quadratic search. PARTIAL is the
single bit between "refuse" and "start the machine that finds compensating
repairs", and per CHANGELOG 0.14.0 it has never been measured on a real multi-bug
situation. The law is right to put the weight there (R4 is exactly this
discriminator); the exposure is in the future measurement, not in the ruling.

F6 - TAUGHT does not gate the PAIR lane; the two PAIR bytes differ only in it.
    1 PAIR 2/256:  x=27 EXHAUSTED|PARTIAL|COUPLED|CHEAP
                   x=59 EXHAUSTED|PARTIAL|COUPLED|CHEAP|TAUGHT
    setting TAUGHT moves 0 inputs into PARTITION/PAIR
docs/PAIR_LAW_PROMPT.md incident 4 calls the taught/coupled/cheap shape "the ONLY
situation in which a pair search ranks first". The law grants the pair with
TAUGHT clear too (x=27, mask 138 - PAIR at bit 1 outranks TEACH at bit 3). The
reach test asserts len(reach)==2 checking only EXH|PAR|COU|CHE, so this was
pinned deliberately; it is the prose that says "ONLY".

F7 - The authored R2 comment at docs/laws/pair.c:27 overstates its scope;
behaviour is the conservative one.
    inputs with DISJOINT set : 128 ; of those NOT ruled PARTITION : 112
       because EXHAUSTED is clear (R1 gate) 64
       because CANCELING is set (R3 veto)   32
       because CAPPED is set (budget spent) 16
    smallest counterexample: x=133 EXHAUSTED|DISJOINT|CAPPED -> CAPPED
"ctz returns the partition whenever one exists, whatever else is true" is true of
the mask, false read as "whenever DISJOINT is observed". src/fluidfix/pair.py:64-66
drops the phrase; the tests scope R2 with not CAN and not CAP.

F8 - 64 of 256 bytes are self-contradictory, and none reaches the quadratic lane.
    inputs asserting BOTH DISJOINT and COUPLED: 64/256
    the law rules: {SINGLE 8, PARTITION 8, REFUSE 32, CAPPED 16}; reaching PAIR: 0
DISJOINT and COUPLED cannot both be true. The byte cannot exclude the
combination; PARTITION owning mask bit 0 means it always falls to the linear answer.

F9 - Total and safe on its documented domain; not outside it.
    documented domain 0..255: masks equal to zero: [] ; outputs outside 0..7: []
    outside: probed 8199; masks zero: 35 -> x=-768 port returns 0 (PARTITION)
             inputs returning a NON-ACT index: 284 -> [(-3840, 8), ...]
    situation(**all eight bits) = 255 ; observe_bits(all true) = 255
Unreachable today: the only caller is src/fluidfix/cli.py:527 iterating
range(256); both public constructors are closed over 0..255. Worth a boundary
check if an actuation is built - the out-of-domain failure mode is
"return 0 = PARTITION", i.e. ACT, not refuse.

F10 - Both documented cost numbers reproduce (arithmetic only; the 1,063 and
3.5 s are quoted from the docs and were NOT re-measured by this agent).
    single-edit candidates on Box2D contact_solver.c : 1063
    naive pair combinations C(1063,2)                : 564453  (doc: 564,453)
    at 3.5 s per candidate: 1,975,586 s = 22.87 days (doc: "about 23 days")
    single-edit pass at 3.5 s: 1.03 h (doc: "~1 hour")

## 4. Lanes
Reached here as verification only - the law has no caller in the body (pair_law
appears only at src/fluidfix/cli.py:527).

| act | inputs/256 | reached | pinned independently of the case table |
|---|---|---|---|
| 0 PARTITION | 16 | yes | yes (R2, incident 3) |
| 1 PAIR | 2 (x=27, 59) | yes | yes (incident 4, reach test) |
| 2 WIDEN | 4 (x=3,19,35,51) | yes | NO |
| 3 TEACH | 5 (x=1,9,11,17,25) | yes | NO |
| 4 BUDGET | 3 (x=33,41,43) | yes | only x=33 (incident 2) |
| 5 CAPPED | 64 | yes | NO |
| 6 SINGLE | 32 | yes | only x=0 (incident 5) |
| 7 REFUSE | 130 | yes | yes for the 128 CANCELING inputs (R3) |

Never reached: NO lane is reachable from a measured situation. CHANGELOG 0.14.0
says so. EXHAUSTED and CHEAP are derivable from data loop.py already holds
(candidate list drained; candidate count vs remaining budget), while PARTIAL,
DISJOINT, COUPLED and CANCELING need per-candidate failing-test-set bookkeeping
that is not retained today. Also: REFUSE(7) collapses two causes - the CANCELING
veto (128 inputs) and "exhausted, no usable evidence" (x=49, 57) - so a report
printing only the act name cannot distinguish them.

## 5. Potential
- PARTITION, 16/256, is the largest acting lane and the cheapest. Documented
  alternative cost on the one refusal with numbers attached (Box2D
  contact_solver.c): 1,063 single-edit candidates vs 564,453 pair combinations.
  What a partition would save on a real multi-bug repo: UNMEASURED - no two-bug
  situation has ever been measured by this project.
- PAIR, 2/256. Value if built: UNMEASURED. Risk if built on a mismeasured
  PARTIAL: one bit (F5).
- WIDEN (4) and TEACH (5) have neither an independent test pin nor an actuation;
  TEACH would hand off to docs/TEACHING.md's teaching path, WIDEN to SIGHT tier 2.
  Both hand-offs exist in the body but are not wired to this law - savings
  UNMEASURED.
- CAPPED, 64/256 - a quarter of the input space - is the least verified act: no
  independent pin, no actuation, and its bit is described only as "clean inputs,
  budget already spent", a phrase defined nowhere except by analogy with
  src/fluidfix/engine.py:22.

## 6. Defects
No wrong ruling found. Three WORDING defects; no observation or actuation defect
(there is no actuation to be wrong).

1. WORDING - src/fluidfix/pair.py:77-79 claims the law is "re-verified
   exhaustively by `fluidfix selfcheck` and tests/test_pair_law.py - all 256
   situations against the specification, R1-R5, and the five incidents".
   selfcheck checks the specification, R1, R2, R3 and the reach count ONLY;
   `grep -n "R4\|R5\|incident" src/fluidfix/cli.py` returns nothing, and the pair
   block is cli.py:526-565. Only the pytest file checks R4, R5 and the incidents.
   CHANGELOG 0.14.0 states it correctly ("the author's three structural rules"),
   so the docstring is the outlier.
2. WORDING - docs/laws/pair.c:27 "whatever else is true" (F7); counterexample
   x=133 -> CAPPED. The ruling is right; the sentence is too strong, and pair.py
   already omits the phrase.
3. WORDING - docs/PAIR_LAW_PROMPT.md incident 4's "the ONLY situation in which a
   pair search ranks first": two bytes rank PAIR first and one has TAUGHT clear
   (F6). The kernel behaves as authored and pinned; the prose does not say so.

Recorded, not defects: the port's shift-loop ctz returns PARTITION rather than
trapping out-of-domain (F9, unreachable today); the 64 self-contradictory bytes
are all ruled to linear or refusing acts (F8).

## 7. Verdict
The PAIR law is exact on all 256 inputs against the authored specification, the C
kernel, and an algebraic re-derivation, with R1-R5 and the five incidents clean;
the only defects are three overstated sentences (docstring, C comment, prompt),
and the real exposure is that 108 of 256 rulings - the whole CAPPED, WIDEN and
TEACH lanes - rest on a case table transcribed three times from one author, while
no lane has any actuation to be wrong in.
