# 47-reshape-actuation

## 1. Target
What RESHAPE means per the engine docstring; whether anything actuates it; whether
`RepairResult.restored_original` is a sound NOTWIN observation; prototype one reshape
on a fixture and measure it.

## 2. Method

Read (all under `/Users/kanchetidevieswar/neo/fluidfix/`):
- `src/fluidfix/engine.py` — the law, `BITS`, `ACTS`, `situation()`, `decide()`, the docstring.
- `src/fluidfix/loop.py` — `RepairResult` (lines 45-69), `_restored_original` (148-161),
  the ruling site `_rule` (193-243, `decide()` at 217, `restored_original` at 226),
  the HIDDEN block (357-392), the search (296-410).
- `src/fluidfix/lanes.py` (EMIT is lowest-bit-first, so kind 0 precedes kind 1),
  `src/fluidfix/acts.py` (`KINDS`, `candidates`).
- `tests/test_guard.py` lines 67-99 — the two shipped pins on `restored_original`.
- `CHANGELOG.md` 438-448 (where `restored_original` came from).
- Prior agents' `research/laws-2026-09-07/FINDINGS.md` (01, 02, 03, 04, 08, 09) for context only.

Wrote and ran (all in this directory; nothing in `src/`, `tests/` or `docs/` was edited;
no git command touched the fluidfix repo):
- `run.sh` — the timeout wrapper this machine lacks: `nice -n 15` + a perl `alarm` that
  kills the child's process group. Self-test: `./run.sh 2 /bin/sh -c 'sleep 30'` -> `rc=124`.
- `reshape_exhaustive.py` -> `reshape_exhaustive.out` — all 256 rulings, the docstring audit,
  the same-index check, the 17 RESHAPE bytes, and what NOTWIN does to every byte the body builds.
- `candidate_probe.py` -> `candidate_probe.out` — which candidate each act emits (no suite runs);
  needed because the literal-off-by-one act emits exactly one candidate and it *decrements*.
- `fixtures.py` — five git scenarios built under `./work/`.
- `notwin_probe.py` -> `notwin_probe.out` — the REAL `loop.repair()` on all five, recording
  `restored_original`, the greens, and what the law would rule under the proposed reading.
  Each scenario carries a **pin** (a stronger check the oracle never saw) that judges whether
  the shipped program is actually correct.
- `reshape_prototype.py` -> `reshape_prototype.out` — an actuated RESHAPE, measured against baseline.

All runs: `./run.sh <seconds> .venv/bin/python <script>`, one at a time.

## 3. Findings

### F1. The engine docstring does not define RESHAPE. At all.

```
$ ./run.sh 120 .venv/bin/python reshape_exhaustive.py       # section A
  occurrences of 'RESHAPE' in engine.py __doc__ : 0
  occurrences of 'NOTWIN'  in engine.py __doc__ : 1
  the only line mentioning either: 'NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set'
  bit -> act pairs the docstring states outright: [('BUILT', 'SHIP'), ('AMB', 'ADD_STATE')]
  bits with NO stated act: ['UNREAD', 'NOTWIN', 'HIDDEN', 'CAPPED', 'REFUTED', 'SELF']
```

The docstring's bit list gives UNREAD/CAPPED/REFUTED their acts in prose too (the regex above
only catches the two whose act sits on the same line); NOTWIN is named exactly once, to say it
is never set. **The specification is silent on what RESHAPE is for.** The task's phrase
"what RESHAPE means per the engine docstring" has no answer in the docstring; the honest
statement is that the meaning is *unspecified in this repo* and is inherited from the upstream
synthesis engine (`github.com/devkancheti4-design/dev`), which is not vendored here — I did not
find any file in the repo defining it (`grep -rn RESHAPE` over `src/ docs/ tests/ CHANGELOG.md`
returns one line: the `ACTS` list itself).

### F2. The only in-repo definition of RESHAPE is structural: it is NOTWIN's act.

```
$ ...reshape_exhaustive.out                                 # section B
  BUILT    (bit 0) -> SHIP                   ACTS[0]=SHIP                   same-index
  AMB      (bit 1) -> ADD_STATE              ACTS[1]=ADD_STATE              same-index
  UNREAD   (bit 2) -> ADD_MATERIAL           ACTS[2]=ADD_MATERIAL           same-index
  NOTWIN   (bit 3) -> RESHAPE                ACTS[3]=RESHAPE                same-index
  HIDDEN   (bit 4) -> CHANGE_GRANULARITY     ACTS[4]=CHANGE_GRANULARITY     same-index
  CAPPED   (bit 5) -> RAISE_BUDGET           ACTS[5]=RAISE_BUDGET           same-index
  REFUTED  (bit 6) -> HARVEST_COUNTEREXAMPLE ACTS[6]=HARVEST_COUNTEREXAMPLE same-index
  SELF     (bit 7) -> SHIP                   ACTS[7]=AUTHOR_SUCCESSOR       DIFFERS
  same-index holds for 7/8 single-bit inputs
```

So RESHAPE means whatever NOTWIN means, and the sense the surrounding vocabulary carries is
the fabrication sense: the material is right, the *shape* is not — re-form it, rather than
spend more budget (RAISE_BUDGET), re-judge at another scale (CHANGE_GRANULARITY) or ask for a
new observable (ADD_STATE). That is a reading of the act names, not a citation; I mark it as
inference, not measurement.

### F3. RESHAPE is actuated nowhere. It occurs exactly once in `src/`.

```
$ grep -rn "RESHAPE" src/
src/fluidfix/engine.py:38:ACTS = ['SHIP', 'ADD_STATE', 'ADD_MATERIAL', 'RESHAPE', 'CHANGE_GRANULARITY',
(count: 1)
```
That single occurrence is the act's own name in the table the law indexes. No branch, no
message, no behaviour. RESHAPE is the emptiest act in the law: CHANGE_GRANULARITY and
HARVEST_COUNTEREXAMPLE at least reach a user-visible string.

### F4. All 17 RESHAPE bytes require NOTWIN, and all 17 also require AMB and UNREAD *clear*.

```
$ ...reshape_exhaustive.out                                 # sections C, D
  count: 17 of 256
  all have NOTWIN set: True
  all have AMB clear:  True
  all have UNREAD clear: True
    x=  8  NOTWIN
    x=  9  BUILT+NOTWIN
    x= 25  BUILT+NOTWIN+HIDDEN
    ...
  bytes with NOTWIN set: 128
  their rulings: {'RESHAPE': 17, 'ADD_STATE': 64, 'ADD_MATERIAL': 32, 'AUTHOR_SUCCESSOR': 15}
```
This is a hard constraint on any NOTWIN design, and it is the finding I did not expect:

```
$ ...reshape_exhaustive.out                                 # section F
  BUILT            -> SHIP
  BUILT+NOTWIN     -> RESHAPE
  BUILT+AMB        -> ADD_STATE
  BUILT+AMB+NOTWIN -> ADD_STATE   (AMB outranks NOTWIN: NOTWIN is INVISIBLE once AMB holds)
```

**Any NOTWIN observation derived from "more than one green" can never produce RESHAPE**, because
a correctly measured AMB is set in exactly those situations and outranks it. For RESHAPE to fire,
NOTWIN must be an observation about a *single, unique* green: one thing was built, nothing
contradicts it inside the suite, and it is still not the thing wanted.

### F5. `restored_original` is not sound as NOTWIN. It inverts in fluidfix's normal case.

`_restored_original` (loop.py:148-161) asks git whether the shipped line equals `HEAD`'s line.
Read as NOTWIN ("the thing built is not the thing wanted" = the repair differs from HEAD), five
real `repair()` runs with a pin the oracle never saw:

```
$ ./run.sh 280 .venv/bin/python notwin_probe.py
scenario                   rest_orig  program   today         proposed   verdict
G1_bug_committed           False      CORRECT   SHIP          RESHAPE    DISAGREES with the pin
G2_uncommitted_exact       True       CORRECT   SHIP          SHIP       agrees
G3_uncommitted_respelled   False      CORRECT   SHIP          RESHAPE    DISAGREES with the pin
G4_no_git                  None       CORRECT   SHIP          SHIP       agrees
G5_wrong_program           False      WRONG     SHIP          RESHAPE    agrees

scenarios where TODAY's ruling matches the pin    : 4/5
scenarios where the PROPOSED ruling matches the pin: 3/5
```

Three independent failure modes, each measured:

- **G1 — it inverts on the ordinary case.** When the defect is committed (which is what a bug
  *is*), HEAD holds the bug, so a *correct* repair necessarily differs from HEAD and reads
  NOTWIN. fluidfix's own shipped test pins this — `tests/test_guard.py:77`:
  `assert report.result.restored_original is False   # the bug WAS committed`, on a
  `status == "repaired"` report. Under the proposed reading, **every correct repair of a
  committed bug rules RESHAPE instead of SHIP.**
  ```
  $ ./run.sh 280 .venv/bin/python -m pytest tests/test_guard.py -k "restored_original or restoration" -q -p no:cacheprovider
  2 passed, 5 deselected in 11.69s
  ```
- **G3 — it measures spelling, not program.** HEAD `if n > 9:`, defect `if n > 10:`; the search
  ships `if n >= 10:`, which is the same program spelled differently. `restored_original` is
  `False`; the pin says CORRECT. This is precisely the case `loop.py:212-215` singles out in as
  many words — *"two SPELLINGS of one program ... refusing those would refuse the commonest bug
  class there is."* The proposed reading refuses it.
- **G4 — it is undefined without git.** `None`, not `False`, and there is no third truth value
  in the byte. A repo with no git (or a shallow/absent HEAD, or a new file) silently loses the bit.

### F6. As shipped, the datum is produced *after* the ruling it would gate, and is read by nothing.

```
$ grep -n "ruling = decide\|res.restored_original = \|if ruling == \"SHIP\"" src/fluidfix/loop.py
217:        ruling = decide(situation(BUILT=True,
221:        if ruling == "SHIP":
226:            res.restored_original = _restored_original(
```
The observation is computed nine lines *after* the law rules, inside the `SHIP` branch, for
`greens[0]` only. Carrying it into the byte means moving the git query above line 217 and running
it per green. Cost measured on a fixture repo: **17.9 ms and 16.7 ms per call** (mean of 20 each),
one `git show` subprocess — negligible beside a suite run (0.4-1.1 s on these fixtures).

```
$ grep -rn "restored_original" src/
src/fluidfix/loop.py:64:    restored_original: bool | None = None
src/fluidfix/loop.py:148:def _restored_original(...
src/fluidfix/loop.py:226:            res.restored_original = _restored_original(
```
Three lines: a declaration, a definition, one write. **Nothing in `src/` reads it** — only two
tests do. It is a dead datum today.

### F7. The reshape prototype: one repair rescued, one destroyed, net zero.

Actuation prototyped (`reshape_prototype.py`): *when the law rules RESHAPE, do not ship
`greens[0]`; re-form at the same site — ship instead the already-green candidate whose shape
matches the wanted shape (HEAD's line). If no green has the wanted shape, refuse.* It re-uses
candidates the search already proved green, so it costs one confirming suite run and no new search.

```
$ ./run.sh 280 .venv/bin/python reshape_prototype.py
scenario                   baseline   prototype  runs      net
G1_bug_committed           CORRECT    refused    3->3      DESTROYED a correct repair
G2_uncommitted_exact       CORRECT    CORRECT    2->2      no change
G3_uncommitted_respelled   CORRECT    CORRECT    3->4      no change
G4_no_git                  CORRECT    CORRECT    3->3      no change
G5_wrong_program           WRONG      CORRECT    3->4      RESCUED a wrong repair

correct programs on disk, fluidfix today : 4/5
correct programs on disk, with RESHAPE   : 4/5
total suite runs today / with RESHAPE    : 14 / 16
```

G5 is the case RESHAPE was supposed to be for: a weak suite (`apply_delta(0,5)==5`) admits two
greens at one site across two candidate sets — `return delta - base` (wrong) and
`return base + delta` (right). The body's AMB proxy misses it (`set_amb=False`, `sites=1`), so
today it ships the wrong program. The reshape swaps in the right one.

It works **only because the right answer was already sitting in `git show HEAD:mod.py`.** That is
not an observation; it is the answer. In G5 the user could have run `git checkout -- mod.py`.
In G1, where the answer is *not* in HEAD, the same actuation destroys a correct repair.

### F8. The case RESHAPE rescues is a case a correctly measured AMB already rules on — without git.

G5 has two greens at one site that are two *different programs*. That is the docstring's own
definition of AMB ("two DIFFERENT candidates both pass the suite"), which agent 04 recorded the
body as under-measuring. With AMB measured by program-difference rather than by site:
`BUILT+AMB -> ADD_STATE` (refuse, ask for one pinning test — `reshape_exhaustive.out` section F),
which is honest and needs no repository history. And from F4, `BUILT+AMB+NOTWIN -> ADD_STATE`
too: fixing the AMB observation removes the only situation where the NOTWIN prototype helped.

## 4. Lanes

Reached by this work:
- `x=9  BUILT+NOTWIN -> RESHAPE` — constructed in `notwin_probe.py`/`reshape_prototype.py` and
  actuated for the first time (in this directory, on a fixture), on G1, G3 and G5.
- `x=1  BUILT -> SHIP`, `x=0 -> SHIP` — the baseline, via the real `loop.repair()`.
- All 256 rulings enumerated in `reshape_exhaustive.py`.

Never reached, and why:
- The other **16 of 17** RESHAPE bytes (`x=8, 25, 41, 57, 73, 89, 105, 121, 137, 153, 169, 185,
  201, 217, 233, 249`). `x=8` is NOTWIN without BUILT — the body's only shipping site
  (`loop.py:217`) hardcodes `BUILT=True`, so a byte with NOTWIN and no BUILT is unconstructible
  there. The other 15 need HIDDEN, CAPPED, REFUTED or SELF alongside NOTWIN; HIDDEN is measured
  but discarded per candidate (`loop.py:391`, agents 08/09), CAPPED never reaches `loop.py:217`
  from the packet path (agent 07), REFUTED is only built at guard-level sites that pass no BUILT,
  and SELF is never measured.
- `AUTHOR_SUCCESSOR` (15 bytes) — also NOTWIN-gated; out of scope here, unreached.
- The 64 `NOTWIN+AMB -> ADD_STATE` and 32 `NOTWIN+UNREAD -> ADD_MATERIAL` bytes: reachable in
  principle the day NOTWIN is measured, but they rule the *same act as without NOTWIN*, so
  nothing observable changes on them.

The observation that would make the RESHAPE lane reachable: any per-green boolean meaning "this
unique green is not the artifact that was wanted". `restored_original` is the only such datum in
the codebase today, and F5 shows it is the wrong one.

## 5. Potential

- **Worth of actuating RESHAPE with `restored_original` as NOTWIN: measured at zero.** 4/5 correct
  programs before, 4/5 after, +2 suite runs (14 -> 16) across the five scenarios. One rescue, one
  destruction. On a corpus of *committed* defects — which is what fluidfix runs on — the measured
  direction is strictly negative: every correct repair reads NOTWIN (F5/G1, and the shipped test
  `tests/test_guard.py:77`). I did **not** measure a repair-rate on a real repo corpus; that number
  is **unmeasured**. What I did measure says the sign is negative before the size matters.
- **Worth of a sound NOTWIN: unmeasured, and structurally narrow.** From F4 it must be a property
  of a *unique* green (anything multi-green is eaten by AMB), which rules out most cheap
  candidates. Two shapes that would qualify, neither measured here and neither implemented:
  (a) a differential observation — the unique green changes behaviour on an input no test pins,
  which needs a reference fluidfix does not have without leaking the answer; (b) a *site*
  disagreement — the unique green edits a line no failing observation ever pointed at (the
  compensating-repair shape described at `loop.py:255-263`). (b) is computable from data
  `loop.py` already holds (`obs.lineno` vs the green's site) and does not consult git. Its value
  is **unmeasured**.
- **Cost of carrying the bit, if one is ever found:** 17 ms per green (F6), versus 0.4-1.1 s per
  suite run on these fixtures. The plumbing is one argument into `_rule` at `loop.py:217`.
- **Cheaper win available in the same neighbourhood:** F8 — the G5 miss is an AMB measurement
  defect (agent 04's D-1), and fixing it turns a wrongly-shipped repair into an honest
  `ADD_STATE` refusal with no new bit and no repository history. Measured here only as the law's
  ruling on the byte (`BUILT+AMB -> ADD_STATE`), not as an end-to-end run of a corrected body.

## 6. Defects

1. **Wording — `src/fluidfix/engine.py:26-28`.** "NOTWIN, HIDDEN and SELF are not yet measured by
   fluidfix and are never set (documented limitation, not an omission by accident)." HIDDEN *is*
   measured and set, at `loop.py:391`. Already recorded by agents 02 and 09; confirmed
   independently here. Not a ruling defect.
2. **Wording — `src/fluidfix/engine.py` docstring, RESHAPE.** The docstring is presented as the
   specification (BRIEF: "read the module docstrings first"), and it defines five of eight acts.
   RESHAPE and AUTHOR_SUCCESSOR have no definition anywhere in the repository (F1, F3), so no
   reader can tell whether a proposed NOTWIN observation matches the author's intent. That is why
   this target had to be answered structurally (F2) rather than by citation.
3. **Actuation — RESHAPE absent (F3).** One occurrence in `src/`, in the `ACTS` table itself.
   Stated as a fact, not a complaint: with NOTWIN unmeasurable the act is correctly dead, and
   building the actuation before the observation would be building a branch that never runs.
4. **Not a defect: the ruling.** On every byte I handed it, `decide()` ruled exactly as its closed
   form says. `BUILT+NOTWIN -> RESHAPE` is right *given* NOTWIN; the whole of F5 is about the bit,
   not the ruling. Under the standing principle: **the failure here is an observation defect in a
   proposal, caught before it was built.**
5. **Dead datum — `restored_original` (F6).** Written at `loop.py:226`, read by nothing in `src/`.
   Not wrong, but it is provenance for a human reader only, and it is *not* the NOTWIN bit.

## 7. Verdict
RESHAPE is undefined by the engine docstring and actuated nowhere (1 occurrence in `src/`); its
17 bytes all require NOTWIN with AMB and UNREAD clear, and reading NOTWIN as
`RepairResult.restored_original` is UNSOUND — it measures byte-equality with git HEAD, so it
inverts on committed defects (fluidfix's normal case, pinned by `tests/test_guard.py:77`), fires
on correct repairs that merely spell the program differently, and is undefined without git; the
prototyped reshape rescued 1 wrong repair and destroyed 1 correct one for +2 suite runs, leaving
4/5 correct programs before and after.
