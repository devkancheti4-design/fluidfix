# 33-incident-audit — every recorded incident, classified
(Relayed by the coordinator: the agent's own write was blocked by a harness rule.
Artifacts on disk beside this file: run.sh, byte_check.py/.out, repro_probe.py/.out,
repro_S1_amb/, suite.out)

## 1. Target
Audit every incident in git log, CHANGELOG.md, docs/ and this session's two waves
against tests/test_law_never_ruled_wrong.py; classify each as observation /
actuation / wording / ruling; list what the test misses; state whether "no defect
has ever lived in a ruling" still holds.

## 2. Method
Read in full: CHANGELOG.md (683 lines, 0.1.0->0.14.0); git log (45 commits,
read-only); tests/test_law_never_ruled_wrong.py; docs/SCALE.md,
PAIR_LAW_PROMPT.md, SIGHT_LAW_PROMPT.md; the coordinator's FINDINGS.md (24
verdicts) and ATTACK_FINDINGS.md (8 verdicts); AND THE UNDERLYING ATTACK.md for
agents 01-09, 11, 13, 17, 18 and REPORT.md for 04, 16, 24 — i.e. the evidence, not
only the logs; source engine.py, loop.py, guard.py, coracle.py, pair.py and eight
test files. Claims taken from another agent's report without re-running are marked
[log]. Every run through run.sh (nice -n 15 + perl alarm on its own process group).

## 3. Findings

F1 — EVERY byte->ruling pair asserted this session re-derives from the shipped law.
0 MISMATCHES OF 29. This is the load-bearing check: if the law's ruling on the byte
an agent says it was handed differed from what the agent reported, the defect WOULD
be in the ruling.
    OK 07 byte passed 513  decide(513)=SHIP            (claimed SHIP)
    OK 07 byte owed   515  decide(515)=ADD_STATE       (claimed ADD_STATE)
    OK 01 owed        517  decide(517)=ADD_MATERIAL    (claimed ADD_MATERIAL)
    OK 08 measured    545  decide(545)=RAISE_BUDGET    (claimed RAISE_BUDGET)
    OK REFUTED+HIDDEN 592  decide=CHANGE_GRANULARITY   (claimed CHANGE_GRANULARITY)
    OK BUILT+SELF     641  decide=SHIP                 (claimed SHIP)
    mismatches: 0

F2 — THE HEADLINE SESSION INCIDENT REPRODUCES FIRST-HAND. Built fresh:
    gate.py: repaired line 5 in 4 suite runs (2.2s):
      - return readings[1] > limit
      + return readings[1] >= limit
    status: repaired  reason: engine law: BUILT -> SHIP   ambiguous: False
    greens: ['    return readings[1] >= limit', '    return readings[0] > limit']
    shipped_equals_pristine: False
    byte PASSED: situation(BUILT=True, AMB=False) = 513 -> SHIP
    byte OWED  : situation(BUILT=True, AMB=True ) = 515 -> ADD_STATE
      alarm([9,1],5): pristine=True  shipped=False
      alarm([0,9],5): pristine=False shipped=True
THE CORRECT PROGRAM WAS greens[1] AND WAS DISCARDED. A wrong repair, not a respelling.

F3 — The defect is ONE EXPRESSION, and it is a measurement. loop.py:217-219:
    ruling = decide(situation(BUILT=True, AMB=set_amb or len(sites) > 1, CAPPED=capped))
set_amb fires only inside ONE candidate set; sites is line numbers. NEITHER ASKS
WHETHER THE GREENS ARE THE SAME PROGRAM. This one expression accounts for SEVEN of
the ten shipped wrong repairs.

F4 — guard.py NEVER reads result.greens, and capped0 can never reach the byte.
    grep -c "greens" src/fluidfix/guard.py  ->  0
repair() has no capped= parameter, so capped0 measured at guard.py:508 cannot reach
loop.py:217. `if result.repaired:` / `if result.ambiguous:` are the only branches —
the third outcome _rule produces, GREEN-BUT-CAPPED, HAS NONE.

F5 — Both oracle-protection filters are LITERAL NAME WHITELISTS.
    guard.py:111-115  base.startswith("test_") or base.endswith("_test.py")
                      or "tests" in parts[:-1] or base == "conftest.py"
    coracle.py:485    re.search(r"(^|/)(tests?|testing)(/|$)", rel_dp)
Four spellings on Python, three directory names on C. test/helpers.py (singular),
ledger/testing.py and unittest/ escape BY CONSTRUCTION.

F6 — Two wording defects confirmed directly in source. engine.py:26-28 states
"NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set";
loop.py:391 is decide(situation(HIDDEN=True)) and has been since 0.13.0 — stale
through two releases. Second: the positional BITS/ACTS tables imply
SELF -> AUTHOR_SUCCESSOR; decide(situation(SELF=True)) is SHIP.

F7 — ZERO of ~55 session defects is classified as living in a ruling. Every hit for
"ruling defect" across research/ is a NEGATIVE finding. No positive.

F8 — THE COORDINATOR LOG UNDERCOUNTS. ATTACK_FINDINGS.md carried 8 agents; 13
ATTACK.md files existed. The five omitted at read time: 06 (S1 5/5 cross-file),
18 (S1a taught class outranks fluidfix's own correct repair; S1b whole-file
SpanEdit), 11 (S2 corruption), 13 (S2 symlink escape; S2 CRLF span), 17 (3x S3
estimate). So "eight wrong repairs" is the count IN THE LOG, not on record: TEN
AGENTS shipped a wrong repair or a corrupted tree. Agents 10, 12, 14, 15, 16, 19,
20 had written no ATTACK.md at read time — UNMEASURED; the table below is a LOWER
BOUND.

F9 — THE CONSOLIDATED INCIDENT TABLE
obs = situation measured wrong · act = act applied wrong or not at all ·
word = report/docstring described it wrong · rule = the law itself

A. HISTORICAL (git log / CHANGELOG / docs) — 33 incidents.
   Classes: act H01,H07,H08,H10,H24,H25,H26,H33 · obs H02,H03,H05,H06,H09,H11,
   H13,H15,H17,H18,H20,H21,H22,H23,H27,H29,H30,H31 · word H04,H14,H16,H19,H28,H32
   Selected, with byte passed -> owed:
     H05 pytest-cov missing, refusal blamed the wrong thing   — -> 516 ADD_MATERIAL   [in test #6]
     H07 zero-padded literal 034->33, GREEN-ONLY IMPOSTOR shipped on click/termui.py:744
     H08 deadline cut a candidate set after one green -> unproven guess shipped
     H09 a signal-filter drop not counted as CAPPED, defeating escalation  0 -> 544
     H20 THE ORACLE IS NOT A CANDIDATE: C guard repaired the runner return 1->0   513 -> SHIP  [in test #1]
     H24 rollback lost when the process was killed                                 [in test #8]
     H27 THE BUILD IS PART OF THE ORACLE: a stale binary made all 35 candidates,
         INCLUDING THE CORRECT ONE, look red                    576 -> HARVEST      [in test #9]
     H29 flaky suite accepted return b - a in 14% of searches   513 -> SHIP; 528 owed [in test #2,#7]
     H30 Unity ProjectOnPlane compensating repair shipped       513 -> 515           [in test #3, as a WIN not an incident]
     H31 deadline paths discarded greens and reported REFUTED   576 -> 545
     H32 0.13.0's published "0 of 49 and 0 of 46" is not the general result
     H33 CHANGE_GRANULARITY ruled and NEVER ACTUATED            528
   THE TEST CARRIES 6 OF THE 33. IT MISSES 26.

B. THIS SESSION — RED TEAM (a wrong repair or corruption actually shipped): 17.
   A01 (07) two greens at ONE line from TWO sets; 12/12 shipped, 6 WRONG,
            byte-identical within each matched pair              513 -> 515  obs
   A02 (09) shipped tax - subtotal; the right repair found in the same run and
            discarded by the tie-break. PLUS S4, the opposite error: a correct
            repair refused for being correct twice               513 -> 515 / 515 -> 513
   A03 (03) 65 defects, 32 detected, 26 accepted, 4 A DIFFERENT PROGRAM
            (12.5% of detected, 15.4% of accepted); 10 of 26 shipped holding a
            second unreported green                              513 -> 515  obs
   A04 (06) cross-FILE compensating repair, 5/5                  513 -> 515  obs
   A05 (18) a taught class outranks fluidfix's own correct repair 513 -> 515  obs
   A06 (01) C harness in unittest/ escapes the regex; shipped a loop that runs
            ZERO TESTS and exits 0                               513 -> 517  obs
   A07 (01) root check.c printing TAP; shipped failures = failures;
            while output still says "assertion failed"           513 -> 517  obs
   A08 (02) ledger/testing.py escapes _is_test_path; the shared assert helper is
            the deepest frame, becomes candidate #1, is edited green, AND THE
            DEFECT FILE IS NEVER OPENED                          0x201 -> 0x203 obs
   A09 (02) helper under test/ (singular) edited to convert failures into SKIPS;
            the cross-examination is blind to `skipped`          0x201 -> 0x203 obs
   A10 (08) truncated packet sets capped0 but repair() derives CAPPED from
            wall-clock only; compensating repair shipped, two routes  513 -> 545 obs
   A11 (04) one honest failing test + one HOLLOW pinning test; all five tautology
            flavours shipped, editing correct code               0x201 -> 0x203 obs
   A12 (05) failure-armed leniency window; shipped on a defect WITH NO CORRECT
            REPAIR IN VOCABULARY. Structural: CONFIRM=k beaten by any window
            >= 2(k+1)                                            528 HIDDEN owed
   A13 (18) SpanEdit anchor check permits a whole-file candidate  act+word
   A14 (11) SIGKILL under repair/jguard + the natural retry POISONS AND DELETES
            the recovery slot. DIRECT DESCENDANT OF TEST INCIDENT #8.  act
   A15 (13) a symlink inside the root written through to a file OUTSIDE it
            (guard.py:137 lexical where realpath is owed)         obs
   A16 (13) the SpanEdit writer drops N-1 CRs from an N-line CRLF span  act
   A17 (17) estimate promised 1.4-7s / 80 runs for a defect costing 34.74s and
            139 runs; refused a C repo it then repaired in 9.15s  obs, 3x S3

C. THIS SESSION — LAW RESEARCH (defects found without a wrong repair): 13 classes.
   L01 guard_once discards BUILT+CAPPED->RAISE_BUDGET while holding a twice-
       confirmed green; greens read nowhere; REFUTED measured as "candidates were
       generated"           built CAPPED=0,REFUTED=1 -> HARVEST; actual CAPPED=1,REFUTED=0 -> RAISE_BUDGET
   L02 the RETRIED veto is DEAD; 41% of logged runs re-tested a rejected pair
   L03 CHANGE_GRANULARITY ruled, never actuated
   L04 LITERAL on the C path is harvested from THE ABSOLUTE CHECKOUT PATH — the
       directory you check out into can decide which file fluidfix looks at first
   L05 FRAMED-as-specified unreachable; an UNFILTERED BASENAME SET reaches the law,
       so a stdlib basename collision promotes an unrelated file to priority 0
   L06 guard.py:131-150 returns traceback files BEFORE sight is imported, and the
       frame branch EXCLUDES the defect file; a 6-run repair becomes a refusal
   L07 the harvest is written on both paths and READ BY NOTHING; coracle never
       calls decide(), so the C refusal blames the vocabulary instead of REFUTED
   L08 loop.py:283 bitmasks obs.kinds: all 720 permutations of a 6-kind line give
       one mask, so class ORDER is unrepresentable and "most specific first" is
       measured then discarded
   L09 the entire Box2D file-ranking gap comes from ONE code-decided sort key,
       coracle.py:735; flipping it moves the true file from median 20 to 3.5
   L10 when the vocabulary yields zero acts the body packs BYTE 0; the law rules
       SHIP, the equality fails, a hardcoded refusal is emitted. That situation is
       the docstring's own definition of UNREAD.       0 -> SHIP; 516 owed
   L11 failing_output() uses -x, so --lf sees one failing test; on a two-bug
       fixture the guard NEVER OPENS THE SECOND FAULT FILE and refuses while its
       own harvest log holds the second fix
   L12 the published 0.13.0 flaky rate is not the general result
   L13 wording set: engine.py:26-28 stale on HIDDEN (verified); BITS/ACTS implies
       SELF->AUTHOR_SUCCESSOR where SELF rules SHIP (verified); pair.c:27 too
       strong; PAIR_LAW_PROMPT incident 4's "the ONLY situation"
   SESSION TOTAL: 17 + 13 = 30, on top of 33 historical. NONE CLASSIFIED AS RULING.

F10 — WHAT THE AUDIT TEST ACTUALLY GUARANTEES.
    pytest tests/test_law_never_ruled_wrong.py -q  ->  4 passed in 0.01s
  1. test_the_law_ruled_correctly_on_every_incident_on_record re-derives 7 of 9
     entries (2 have expect=None). REAL, and it passes.
  2. test_no_defect_has_ever_lived_in_the_ruling asserts a HAND-WRITTEN `where`
     column contains no RULING. A SELF-DECLARATION, NOT A DETECTOR — nothing in
     the build can put RULING there.
  3. test_the_audit_carries_real_incidents_not_only_clean_cases is
     assert len(real) >= 5 with 6 present. THE FLOOR IS 5, SO IT CAN NEVER FAIL
     FOR UNDER-RECORDING — the list could omit 50 incidents and stay green.
  4. test_ship_is_not_a_veto_and_amb_is_the_brake pins 513->SHIP and 515->
     ADD_STATE. Both correct — AND BOTH ARE EXACTLY THE BYTES A01-A05, A08-A11
     WERE OWED AND NEVER GIVEN.
  The audit records 6 incidents against 33 historical + 30 session.

## 4. Lanes
Reached: SHIP (live, F2); ADD_STATE (as the OWED ruling on 515 in nine session
incidents, live only in the two shapes set_amb/sites>1 do measure); ADD_MATERIAL
(516/517, owed for A06/A07/L10); RAISE_BUDGET (33/544/545, owed for A10/L01);
HARVEST_COUNTEREXAMPLE (576, the ruling actually asked at guard.py:539,612,618);
CHANGE_GRANULARITY (528/592 as a ruling — never actuated).
Never reached by anything on record: RESHAPE and AUTHOR_SUCCESSOR. All 32 bytes
ruling either act have NOTWIN set; NOTWIN is measured nowhere in src/; SELF unlocks
zero acts. Two of eight acts have no incident, no test and no call site.
Not reached directly: ranking, SIGHT, PAIR, router, lanes — evidence for those is
other agents' reports, read but not re-run, and marked so.

## 5. Potential
- ONE MEASUREMENT CLOSES SEVEN OF THE TEN SHIPPED WRONG REPAIRS. A01-A05, A08,
  A09, A11 all pack AMB=0 while greens holds two behaviourally different programs.
  A differential probe over greens already in memory costs 0.1 ms, ~2,000x cheaper
  than one suite run; a simpler form is AMB = len(greens) > 1. Measured on this
  agent's own reproduction: greens had length 2 at ruling time, so the corrected
  byte is 515 -> ADD_STATE — a refusal instead of a wrong repair, AT ZERO EXTRA
  SUITE RUNS.
- ONE PARAMETER CLOSES A10 AND L01. repair() has no capped= channel, so capped0 —
  already measured at guard.py:508 — never reaches the byte.
- Adding this session's incidents to the list costs nothing and is the only thing
  that keeps the central claim checkable. It already degrades silently: 0.14.0's
  own CHANGELOG records three incidents (H31, H32, H33) never added to the file
  that release introduced.
- Value of RESHAPE / AUTHOR_SUCCESSOR: UNMEASURED — no incident on record for either.
- Whether the 12.5% wrong-program rate holds on well-tested repos: UNMEASURED.

## 6. Defects (in the audit apparatus, not in src/)
1. WORDING/PROCESS — the audit list is stale by two releases and one whole session.
   9 entries covering 6 incidents; this audit counts 33 historical + 30 session.
   Its docstring says it audits "every incident on record"; it does not.
2. WORDING — test_the_audit_carries_real_incidents_not_only_clean_cases cannot
   enforce what its name says (>= 5 with 6 present).
3. WORDING — test_no_defect_has_ever_lived_in_the_ruling is a DECLARATION, NOT A
   DETECTOR. The build cannot discover a ruling defect; it can only record one a
   human already classified.
4. OBSERVATION (in src/), confirmed first-hand: loop.py:217-219 measures AMB as
   PROVENANCE, never PROGRAM IDENTITY; guard.py reads result.greens zero times and
   has no capped= channel. These two sites are behind TEN of the seventeen
   red-team incidents.
5. WORDING (in src/): engine.py:26-28 stale on HIDDEN.
6. RULING — NONE FOUND. 29 of 29 byte->ruling pairs re-derive from the shipped law;
   no report classifies any defect as ruling.

COULD NOT VERIFY, stated as such:
- Agent 21's wording defect on pair.py:77-79 — NOT CONFIRMED. tests/test_pair_law.py
  DOES contain test_r4_*, test_r5_* and five test_incident_* functions, so
  "re-verified by fluidfix selfcheck AND tests/test_pair_law.py — R1-R5, and the
  five incidents" is accurate read as a JOINT claim, and overstates only selfcheck
  alone. Recorded as CONTESTED, not confirmed.
- Agent 05's flaky rates and agent 17's Box2D medians — not re-run; UNMEASURED,
  taken from their reports.
- Adversarial agents 10, 12, 14, 15, 16, 19, 20 — no ATTACK.md existed at read
  time. UNMEASURED; section B is a LOWER BOUND.
- The full pytest tests/ run did not finish inside the 290s wrapper on this
  50-agent machine (suite.out stops at 36%). The whole-suite pass count is
  UNMEASURED; the audit test itself passed 4/4.

## 7. Verdict
The claim survives — 29 of 29 byte->ruling pairs on record re-derive exactly from
the shipped law and not one of this session's ~30 new defects lives in a ruling —
BUT THE TEST THAT GUARDS IT DOES NOT: it carries 6 incidents against the 63 now on
record, its floor of 5 means under-recording can never fail the build, and it would
not have caught a single one of the ten wrong repairs the red team shipped,
including the one reproduced here from scratch.
