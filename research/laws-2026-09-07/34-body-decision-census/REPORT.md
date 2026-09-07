# 34-body-decision-census

## 1. Target

Every branch in `loop.py`, `guard.py`, `acts.py`, `oracle.py`, `coracle.py` that chooses
between repair OUTCOMES rather than plumbing a measurement, listed with its line number
and classified as law-ruled or code-decided.

## 2. Method

Read in full: `src/fluidfix/{loop,guard,acts,oracle,coracle}.py` (2,591 lines), plus
`engine.py`, `sight.py` and the `lanes.py` API as the specifications to classify against.

Scripts in this directory (all runnable; `nt.sh` is the nice + perl-alarm timeout wrapper
written because this machine has no coreutils `timeout` -- verified `rc=124` on a 30s sleep
under a 2s cap):

| script | what it does | output |
|---|---|---|
| `nt.sh SECS cmd...` | `nice -n 15` + perl `alarm`, kills the process GROUP | -- |
| `enumerate_branches.py` | AST walk: every `If`/`IfExp`/`While`/`BoolOp`/comprehension-`if` in the five files | `branches_all.txt` |
| `census.py` | joins that enumeration against the hand classification; proves completeness | `CENSUS.txt` |
| `verify_rulings.py` | re-derives the engine law for every situation the body can construct | `verify_rulings.out` |
| `verify_mask_order.py` | drives `lanes.mask_of/EMIT/ADVANCE/HALT` exactly as `loop.py:283-298` does | `verify_mask_order.out` |
| `verify_refuted.py` | live `repair()` run on `fixture_refuted/`, then guard.py's own expressions verbatim | `verify_refuted.out` |

`fixture_refuted/` is a two-file pytest project built here (the target named no fixture);
the sleep in its test makes the deadline path deterministic rather than a race.
One real suite run only, under `nt.sh 280`. No repo was copied; no defect injection was
needed for this target.

**The full census table is `CENSUS.txt`** -- 120 entries, each with the source line, what it
chooses, and its basis. This report carries the findings, not the table.

## 3. Findings

### 1 -- The census: 120 outcome-choosing decisions; 92 (77%) are code-decided.

    $ ./nt.sh 60 .venv/bin/python census.py   # -> CENSUS.txt
      branch points enumerated in the 5 files : 293 distinct lines (344 nodes; some lines hold >1)
      branches that choose a repair OUTCOME   : 120
      of those, by verdict                    : {'CODE': 92, 'LAW-INPUT': 10, 'LAW': 14,
                                                 'LAW-QUOTED': 1, 'TAUTOLOGY': 3}
      by file            : {'loop.py': 27, 'guard.py': 40, 'acts.py': 9, 'oracle.py': 9,
                            'coracle.py': 35}
      LAW or LAW-INPUT   : 24/120 (20%)
      CODE-DECIDED       : 92/120 (77%)

Verdicts: **LAW** = a ruling steers the branch. **LAW-INPUT** = measures a bit the law
reads, with the threshold taken from a law docstring. **LAW-QUOTED** = `decide()` is
called but its return only enters a string. **TAUTOLOGY** = `decide()` is called on a
*literal* byte, so the branch cannot vary. **CODE** = the body chose; no law was asked.

Nine of the most consequential decisions are **not `if` statements at all** -- they are sort
keys and ordered tuple literals. A census that counted only `if` would miss every one:

    acts.py:126     for a, b in ((">=", ">"), ("<=", "<"), (">", ">="), ("<", "<=")):
    acts.py:248     for a, b in (("<=", ">="), (">=", "<="), ("<", ">"), (">", "<")):
    coracle.py:550  ordered += [r for r, _ in sorted(scored.items(),
    coracle.py:735  extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))
    guard.py:284    failonly=specificity >= 0.9,
    guard.py:300    ranked2.sort(key=lambda t: (file_priority2(t[3], t[1], t[2]),
    guard.py:302    return [rel for _, _, _, rel in ranked2[:max(limit, 8)]]
    guard.py:412    dense=shapes.get(_shape(body), 0) >= 8,
    guard.py:425    order = sorted(range(len(observations)),

### 2 -- There are six `decide()` calls in the body. Two carry a variable byte.

    $ grep -n "decide(" loop.py guard.py acts.py oracle.py coracle.py
    loop.py:217:        ruling = decide(situation(BUILT=True,
    loop.py:391:                            ruling = decide(situation(HIDDEN=True))
    guard.py:491:    if decide(situation(UNREAD=True)) == "ADD_MATERIAL":
    guard.py:539:    if escalate and decide(situation(CAPPED=capped0, REFUTED=acts0)) == "RAISE_BUDGET":
    guard.py:612:            decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":
    guard.py:618:        decide(situation(REFUTED=True)) == "HARVEST_COUNTEREXAMPLE":

    $ ./nt.sh 60 .venv/bin/python verify_rulings.py
    === A. The three constant-byte decide() calls in guard.py ===
      guard.py:491  UNREAD=True   -> ADD_MATERIAL   (byte is a literal: branch is a tautology)
      guard.py:612  REFUTED=True  -> HARVEST_COUNTEREXAMPLE   (byte is a literal: ...)
      guard.py:618  REFUTED=True  -> HARVEST_COUNTEREXAMPLE   (byte is a literal: ...)

- **loop.py:217** -- variable (BUILT/AMB/CAPPED). Steers `if ruling == "SHIP"` at :221.
  This is the one place in 2,591 lines where a ruling alone decides an outcome.
- **guard.py:539** -- variable (CAPPED/REFUTED). Steers escalation.
- **guard.py:491, :612, :618** -- the byte is a literal, so the comparison is a tautology.
  They are law *citations* in a report string, not consultations. Note also that
  `UNREAD -> ADD_MATERIAL` at :491 sets only a `hint` string: nothing is actuated.
- **loop.py:391** -- decorative. The ruling enters only the `why` f-string at :396; the
  actual act (`ok = False` at :388, rejecting the candidate) is the body's own.

`acts.py`, `oracle.py` and `coracle.py` contain **zero** law consultations of any kind:

    $ for f in loop.py guard.py acts.py oracle.py coracle.py; do echo "--- $f"; \
        grep -n "from \.\(engine\|rank\|sight\|pair\|router\|lanes\)" $f; done
    --- loop.py     38:from .engine import decide, situation
                    39:from .lanes import ADVANCE, EMIT, HALT, kind_of, mask_of
    --- guard.py    216:from .sight import observe_bits as _sight_bits, sight as _sight
                    356:from .rank import observe_bits, rank as _rank
                    460:from .engine import decide, situation
    --- acts.py     29:from .router import route
    --- oracle.py   (none)
    --- coracle.py  (none)

### 3 -- loop.py:230 re-tests the facts it just fed the law. Confirmed; today it agrees.

`loop.py:217-219` feeds `AMB=set_amb or len(sites) > 1` to `decide()`. Eleven lines later
`loop.py:230` re-evaluates that same expression instead of reading the ruling it just got.
This is not cosmetic: the branch sets `res.ambiguous`, which `guard.py:525` and `:606` use
to **stop searching every remaining candidate file**.

Measured over all four bytes the site can construct (BUILT is always True there):

    $ ./nt.sh 60 .venv/bin/python verify_rulings.py
    === B. loop.py:221/230 -- is `set_amb or len(sites)>1` the same test as ruling=='ADD_STATE'? ===
        AMB=0 CAPPED=0 -> law=SHIP          body branch at :230 -> CAPPED wording      OK
        AMB=0 CAPPED=1 -> law=RAISE_BUDGET  body branch at :230 -> CAPPED wording      OK
        AMB=1 CAPPED=0 -> law=ADD_STATE     body branch at :230 -> AMBIGUOUS wording   OK
        AMB=1 CAPPED=1 -> law=ADD_STATE     body branch at :230 -> AMBIGUOUS wording   OK
      mismatches: none

**Stated precisely: this is a duplicated predicate, not a live divergence.** It agrees with
the law on 4 of 4 constructible bytes today. It is a hazard because agreement is
coincidental -- `AMB=1, CAPPED=1` rules ADD_STATE only because the law happens to give AMB
precedence; a re-authoring that changed that precedence would silently desynchronise the
body. `if ruling == "ADD_STATE"` is the same code and cannot desynchronise.
The same predicate is written a **third** time at `loop.py:415`.

### 4 -- guard.py:519 measures REFUTED as "candidates were generated", and it is wrong.

`engine.py:24` defines the bit as *"candidates were generated **and the suite rejected
every one**"*. `guard.py:519` measures `acts0 = acts0 or bool(result.acts_tried)`, and
`acts_tried` is appended at `loop.py:336` when a candidate *set starts* -- the second
clause is never checked. A live run reaching the BUILT+CAPPED lane produces `acts_tried`
non-empty **and** `greens` non-empty at the same time:

    $ ./nt.sh 280 .venv/bin/python verify_refuted.py
    baseline suite green? False
    elapsed 3.7s
      repaired : False
      ambiguous: False
      greens   : ['    return a + b']
      acts_tried: [8]
      reason   : a candidate passes, but the search was cut short before it could be shown
                 unique ... (engine law: BUILT+CAPPED -> RAISE_BUDGET)

    --- now guard_once's own expressions, verbatim, on this result ---
      guard.py:519  acts0 = acts0 or bool(result.acts_tried)  -> True
                    but a candidate PASSED the suite: res.greens = ['    return a + b']
      guard.py:538  capped0 -> False   (the DEADLINE cap that repair() just ruled
                    RAISE_BUDGET on is never propagated here)
      guard.py:539  decide(situation(CAPPED=False, REFUTED=True)) = HARVEST_COUNTEREXAMPLE
                    == 'RAISE_BUDGET'? False  -> escalation SKIPPED
      guard.py:617  acts0 and decide(...)=='HARVEST_COUNTEREXAMPLE' -> True
      => guard would return status='refused' with hint:
         "every generated candidate was rejected by the suite
          (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE)"

Three consequences, all from mismeasurement, none from a ruling:

1. **A false claim.** The user is told every candidate was rejected. One passed.
2. **The escalation the law ordered is skipped.** `repair()` got RAISE_BUDGET at
   `loop.py:217`; `guard.py:539` asks a *different* question about the same episode and
   gets HARVEST_COUNTEREXAMPLE.
3. **The passing candidate is discarded silently.** `GuardReport` has no `greens` field,
   and the `guard.py:622` return passes `result=None`, so it never reaches the user.

Second, independent mismeasurement on the same line-group: `capped0` is measured only from
`packet.truncated` (`:508`) and a truncated file list (`:538`). The **first-pass deadline**
(`first_deadline`, `guard.py:468`) that actually capped this search is never propagated,
so CAPPED reads 0 on a search that was demonstrably capped.

### 5 -- loop.py:283 collapses class order into a bitmask, inverting the observer's priority.

`acts.py:60` documents `Observation.kinds` as **"most specific first"**. `loop.py:283`
does `mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)`, and `lanes.EMIT` then takes
the lowest live bit.

    $ ./nt.sh 60 .venv/bin/python verify_mask_order.py
      observer said kinds=[3, 1]      -> body tries kinds in order [1, 3]
      observer said kinds=[1, 3]      -> body tries kinds in order [1, 3]
      observer said kinds=[12, 0]     -> body tries kinds in order [0, 12]
      observer said kinds=[10, 0, 1]  -> body tries kinds in order [0, 1, 10]
      observer said kinds=[8, 3]      -> body tries kinds in order [3, 8]

The observer's ordering is discarded; the effective priority is the ascending kind number,
and kind numbers come from the `KINDS` dict literal at `acts.py:74-114` -- a code decision.
The lanes law rules the *traversal* of a mask; it was never given the *priority*. Under a
deadline this changes which repair is found, because `loop.py:222` ships `greens[0]`.

### 6 -- coracle.py orders candidate files three separate ways, and asks no law at any of them.

`guard.py:300` sorts files by `sight()`. The C path has three independent orderings and
calls `sight()` at none of them:

    coracle.py:507  assert frames first (append order)
    coracle.py:550  ordered += sorted(scored.items(), key=(-score, -file_SIZE, name))
    coracle.py:553  nothing pointed anywhere -> sorted(srcs.values(), key=(-file_SIZE, name))
    coracle.py:735  extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))

`coracle.py:735` is the measured one. Agent 17 (`../17-sight-real-files/REPORT.md:115-117`)
injected 20 defects into Box2D and measured that **flipping the `len(fail_cov[r])` tiebreak
from ascending to descending alone moves the true file from median rank 20 to median 3.5,
top-3 from 4/16 to 8/16.** I verified the direction in the code, not the corpus: the key is
ascending (fewest executed lines first), justified in the comment at `:734` as "cheapest to
search first among equals" with no law and no measurement behind it. Agent 17 also measured
that adding `sight()` itself is worth only -0.5 places on that corpus (their controls A vs
D) -- so the value is in the *tiebreak direction*, a pure code decision, not in the law.

Worth recording: coracle already **measures five of `sight()`'s eight bits** and throws them
into ad-hoc keys instead -- FRAMED (`:504-508`), NAMED (`:520-541`), FAILONLY and UBIQUITOUS
(both from `_spec` at `:724-729`), SMALL (`len(fail_cov[r])` at `:735` is exactly SIGHT's
executed-line count). Only SCARCE, LITERAL and TOUCHED are unmeasured on the C path.

### 7 -- Two CAPPED sources are measured and then discarded; one is never measured.

    $ grep -rn "\.truncated" *.py
    guard.py:508:        capped0 = capped0 or packet.truncated
    guard.py:509:        if not packet.truncated:
    guard.py:579:            if packet is not None and packet.truncated \

`build_packet_c` computes `truncated` at `coracle.py:656` and its docstring (`:569`) says it
carries "the same truncation semantics the engine law's CAPPED ruling reads". **No line in
`coracle.py` ever reads it** -- the three readers are all on the Python path. `cguard_once`
has no escalation stage at all, so the C guard measures CAPPED and drops it.

    $ grep -n "candidate_cap\|CAPPED" acts.py loop.py
    acts.py:406:            if isinstance(c, (str, SpanEdit))][:candidate_cap()]
    loop.py:219:                                  CAPPED=capped))

`acts.py:406` truncates every candidate set at 32 -- described at `acts.py:366` as "a BUDGET,
not a safety limit" -- and sets no flag anywhere. `loop.py` only ever passes the *deadline*
flag as CAPPED. A search cut short by the candidate cap reports CAPPED=0.

### 8 -- `escalate` can veto the law by short-circuit.

`guard.py:539` reads `if escalate and decide(...) == "RAISE_BUDGET"`. With `escalate=False`
Python short-circuits and `decide()` is **never called**: the law is not overruled, it is
not asked. Stated precisely and without overstating it: no CLI flag sets this today --
`grep -n "no-escalate\|no_escalate" cli.py` returns nothing, and `escalate: bool = True` at
`guard.py:442` is only reachable by a programmatic caller. It is a latent veto, not a live
one.

## 4. Lanes

Reached by this work -- the engine law's rulings the body can actually construct:

    $ ./nt.sh 60 .venv/bin/python verify_rulings.py
    === D. ===
      situations the body can construct: 10 of 256
      acts reached: ['ADD_MATERIAL', 'ADD_STATE', 'CHANGE_GRANULARITY',
                     'HARVEST_COUNTEREXAMPLE', 'RAISE_BUDGET', 'SHIP']
      acts NEVER reached: ['AUTHOR_SUCCESSOR', 'RESHAPE']

Ten of 256 situations are constructible from the six `decide()` call sites, and only three
of those ten come from a variable byte (`loop.py:217`'s AMB x CAPPED and `guard.py:539`'s
CAPPED x REFUTED). ADD_MATERIAL, CHANGE_GRANULARITY and HARVEST_COUNTEREXAMPLE are reached
only as *strings in report text*, never as actuated acts.

Never reached, and why: **RESHAPE** needs NOTWIN, **AUTHOR_SUCCESSOR** needs SELF; both are
documented at `engine.py:27-28` as unmeasured. Nothing in the five files sets either bit.

The SIGHT law is reached at `guard.py:300` -- but only when the traceback names no source
file. `guard.py:146-150` returns the frame-ordered list and `sight()` is never called on
that path. The RANK law is reached at `guard.py:425` on every path. The lanes law is
reached at `loop.py:284/297/298` on every path. The PAIR law is not imported by any of the
five files.

## 5. Potential

- **Reading `ruling` instead of re-deriving it** (`loop.py:230`, `:415`): worth zero
  outcomes today -- measured, 0 of 4 constructible bytes disagree (Finding 3). Its value is
  that it *cannot* desynchronise later. Unmeasured beyond those 4 bytes.
- **Measuring REFUTED as the law defines it** (`guard.py:519`): converts one false refusal
  message per BUILT+CAPPED episode into the truth, and restores the escalation pass the law
  ordered. Demonstrated on one fixture (Finding 4). How often that lane fires on a real
  corpus is **unmeasured**.
- **Propagating the deadline cap into `capped0`** (`guard.py:508/538`): would make
  `decide(situation(CAPPED=True, REFUTED=True))` -> RAISE_BUDGET fire instead of the current
  HARVEST_COUNTEREXAMPLE. Measured only as the law's ruling table (Finding 4, section C);
  the repair yield is **unmeasured**.
- **`coracle.py:735`'s tiebreak direction**: median rank 20 -> 3.5 on 16 Box2D defects,
  i.e. ~16.5 fewer candidate files opened per defect -- measured by agent 17, verified by me
  only at the level of the code being ascending. This is the largest measured number
  attached to any single code-decided site in the census.
- **Giving the law a CAPPED bit for the 32-candidate cap** (`acts.py:406`) and reading
  `packet.truncated` on the C path (`coracle.py:656`): both are already measured and thrown
  away, so the cost is plumbing, not observation. Yield **unmeasured**.
- **Preserving observer priority** (`loop.py:283`): would need the law to rule on class
  order rather than mask traversal -- the RANK law already ranks *lines* and could rank
  classes. Yield **unmeasured**; agent 13's target covers the recurrence data.

## 6. Defects

1. **`guard.py:519` -- OBSERVATION.** REFUTED is measured as `bool(acts_tried)`
   ("candidates were generated") where `engine.py:24` requires "and the suite rejected every
   one". Evidence: `verify_refuted.out`, a live `repair()` returning `acts_tried=[8]` and
   `greens=['    return a + b']` simultaneously. The ruling was never wrong; the byte was.
2. **`guard.py:508`/`:538` -- OBSERVATION.** CAPPED is measured from packet truncation and
   file-list truncation only; the first-pass deadline (`guard.py:468`) that capped the
   search is not propagated. Same evidence run: `capped0 -> False` on a search that
   `repair()` had just ruled BUILT+CAPPED on.
3. **`guard.py:617-621` -- WORDING** (consequence of 1). The refusal states "every generated
   candidate was rejected by the suite" when one passed. Compounded by `GuardReport` having
   no `greens` field and `result=None` on the `guard.py:622` return, so the passing
   candidate is not merely mis-described -- it is unreachable.
4. **`coracle.py:656` + `cguard_once` -- ACTUATION.** `truncated` is computed and documented
   as the CAPPED input, and no C-path code reads it; there is no escalation stage in
   `cguard_once`. Evidence: `grep -rn "\.truncated" *.py` returns three hits, all in
   `guard.py`.
5. **`acts.py:406` -- OBSERVATION.** The 32-candidate budget truncates a set and sets no
   CAPPED bit. Evidence: `grep -n "candidate_cap\|CAPPED" acts.py loop.py`.
6. **`loop.py:391` -- ACTUATION (minor).** The HIDDEN consultation's ruling
   (CHANGE_GRANULARITY) is interpolated into a string; the act performed (`ok = False`,
   `loop.py:388`) is chosen by the body. The outcome is defensible -- the re-check at
   `:381-385` *is* a granularity change -- but the law's return steers nothing.

**No ruling was found to be wrong.** Every defect above is an observation, an actuation, or
a wording, consistent with the standing principle.

## 7. Verdict

Of 120 outcome-choosing decisions across the five body files, 92 (77%) are code-decided and
only one -- `loop.py:221` -- is steered by a ruling alone; of the body's six `decide()` calls,
three are tautologies on a literal byte and one is decorative, leaving two live
consultations, and one of those (`guard.py:539`) is fed a REFUTED bit that a live run shows
reads True while a candidate is passing the suite.
