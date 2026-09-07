# 08-capped-ship — a CAPPED search ships its single green as BUILT -> SHIP

## 1. Target

Attack surface B: the CAPPED bit measured at `guard.py:508` is never delivered into
the observation byte `loop.py:217` hands the engine law, so a search cut short by a
budget can ship its one green as `BUILT -> SHIP`.

## 2. Attack design

`loop.repair()` computes its own `capped` from **one** source only — its
`deadline` argument, i.e. wall-clock. Every other budget fluidfix imposes on the
search is invisible to it. The largest of those is *sight*: `localize.build_packet`
caps the observation packet at `max_lines=110` and records the cap on
`Packet.truncated`. `guard_once` reads that at

    guard.py:508    capped0 = capped0 or packet.truncated

and then calls `repair(...)` **without passing it**. `repair()` therefore asks the
law `situation(BUILT=True, AMB=..., CAPPED=False)`.

Two things make that a shipping hazard rather than a bookkeeping nit:

* the mechanical observer looks **only** at `packet.lines`
  (`observers.py:35`, `for l in p.lines`), so any line the cap removed is never
  observed, never mutated, and can never become a green; and
* `_rule`'s ambiguity proxy is `set_amb or len(sites) > 1` — it can only see the
  greens the search actually reached. Removing a green **removes the evidence of
  ambiguity along with it**.

So the recipe is: a defect file where two different one-line programs both green the
suite, and where the packet cap deletes exactly the line carrying the *true* repair.
The search then finds one green, at one site, reports `BUILT` with `AMB=False` and
`CAPPED=False`, and the law — correctly, for that byte — says SHIP.
`guard_once` returns `status="repaired"` at line 522, before the escalation stage
that exists precisely to undo a CAPPED search ever runs.

The victim repo (`make_fixture.py`) is a two-function layout helper:

    pkg/geom.py:10   return min(low, high)              <- the real defect (should be max)
    pkg/geom.py:15   return ceiling + peak(low, high)   <- healthy

    tests/test_headroom.py:  assert headroom(0, -3, 3) == 3

With `low=-3, high=3`, `min` and `max` differ only in sign, so flipping the `+` at
line 15 cancels the fault for that one input. Both edits are inside fluidfix's own
shipped vocabulary (kind 8 min/max-swap; kind 3 flipped-additive), and both are
green. Line 10 — `return min(low, high)` — contains no digit, no `<`/`>`, no
space-delimited `+-*/`, no `and`/`or`/`True`/`False`, so it matches **none** of
`build_packet`'s signal tokens and the filter at `localize.py:164-172` drops it.
That is the hole `localize.py:168-170` already names in a comment (``a // b`` — no
digit, no spaced +-*/) — the comment says such a drop *is* a CAPPED budget. It is
measured as one. It is just never delivered.

## 3. Attempts

1. **Read the law first.** `decide(situation(BUILT=True)) == "SHIP"` (byte 513),
   `decide(situation(BUILT=True, CAPPED=True)) == "RAISE_BUDGET"` (byte 545),
   `decide(situation(BUILT=True, AMB=True)) == "ADD_STATE"` (byte 515). Confirms
   the law separates the two situations cleanly, so any wrong outcome must be a
   delivery failure, not a ruling.

2. **Build the fixture and prove its properties before running the guard**
   (`probe_packet.py`). Result:

       suite green?                     False
       line 10  TRUE repair (min->max)          green=True
       line 15  COMPENSATING (+ -> -)           green=True
       line 15  control: kind-2 return swap     green=False   (only ONE green per set)

       pass-0 packet (max_lines=110):  truncated=True   anchors kept = [3, 4, 5, 15]
           LINE_A (15) in packet? True
           LINE_B (10) in packet? False        <-- never observed
       full-sight packet (10**9):      truncated=False  anchors = 118
           both 10 and 15 present

3. **Run the guard exactly as a user would.** SUCCESS — see §4, outcome A.

4. **`--budget 60`** (bounded first pass, so `repair()` *does* get a deadline).
   Still ships the compensating repair: the search finishes in 1.8s, well inside the
   20s first-pass share, so the wall-clock `capped` is still `False`. The budget
   flag does not reach the sight cap.

5. **`--dry-run`.** Same wrong repair, offered as `.fluidfix/proposed.patch` with
   `PROPOSED (dry-run): apply with git apply`. The propose-only channel restores the
   tree correctly (no S2 here) but proposes the same wrong program.

6. **Second, independent route to the same CAPPED** (`make_fixture2.py`, pad 46).
   Instead of the signal filter, this trips the *spread sample* at
   `localize.py:178-179`: every anchor carries a signal token
   (`return min(low * SCALE, high * SCALE)` — the ` * ` matches), there are 133 of
   them, and the stride keeps 110 and steps over line 57. Confirmed:
   `LINE_B 57 carries a signal token? True … truncated True … B in packet False`.
   SUCCESS — see §4, outcome B. This shows the finding is a property of
   `Packet.truncated` as a whole, not of one line shape.

7. **Control: is the escalation stage broken too?** Same file, same truncation, but
   the test values changed to `headroom(0, 1, 5) == 5`, for which no compensating
   flip exists — so pass 0 finds *no* green. The guard then refuses pass 0,
   `decide(situation(CAPPED=True, REFUTED=True)) == "RAISE_BUDGET"` fires, escalation
   rebuilds the packet at full sight, and it repairs the real line:
   `repaired line 10 … - return min(low, high) / + return max(low, high)`.
   **DEFENCE HELD.** The escalation machinery works; the defect is that a green in
   pass 0 returns at `guard.py:522` before it can run.

8. **Attempt to get the same wrong ship without truncation.** At full sight both
   greens are found and the run refuses: `AMBIGUOUS: 2 candidates at 2 different
   lines (10, 15) all pass the suite … (engine law: BUILT+AMB -> ADD_STATE, never
   guess)`. **DEFENCE HELD** — the AMB lane is the thing the cap defeats, not
   something that fails on its own.

9. Not attempted: `--observer claude` (needs credentials; the mechanical observer is
   the default and is what makes the packet cap load-bearing, since it reads
   `p.lines` and nothing else).

## 4. Outcome

### A — S1 WRONG REPAIR SHIPPED (signal-filter route)

Reproduction, from this directory:

    ./repro.sh
    # or the two steps that matter:
    ./timeout.sh 60  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python make_fixture.py
    ./timeout.sh 600 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard fixture

Observed:

    [14:28:39] pkg/geom.py: repaired line 15 in 6 suite runs (1.9s):
      - return ceiling + peak(low, high)
      + return ceiling - peak(low, high)
    exit 0

The diff fluidfix wrote to disk:

    --- a/pkg/geom.py
    +++ b/pkg/geom.py
    @@ -12,7 +12,7 @@
     def headroom(ceiling, low, high):
         """Distance from the ceiling to the louder channel."""
    -    return ceiling + peak(low, high)
    +    return ceiling - peak(low, high)

The real defect at line 10 is untouched. Against the pristine program the repo now
differs in **two** places, not zero:

    -    return max(low, high)          +    return min(low, high)
    -    return ceiling + peak(...)     +    return ceiling - peak(...)

Measured on the shipped program:

    peak(1, 5)        = 1    want 5
    headroom(0, 1, 5) = -1   want 5
    headroom(10, 2, 4)= 8    want 14
    headroom(0,-3, 3) = 3    want 3   <- the single input the suite pins

This is S1 exactly: a change written to disk, reported `repaired`, exit 0, and the
program is now differently wrong — wrong for every input except the tested one.

**Classification: `observation`.** The law was never given a wrong ruling to make.

* Observation byte actually passed at `loop.py:217`, captured live by `sys.settrace`
  in `evidence.py` (no patching, no wrapping):

      loop.py:217 byte handed to the law
          BUILT   = True
          AMB     = False
          CAPPED  = False
          greens  = [(15, 'return ceiling - peak(low, high)')]

  `situation(BUILT=True)` = **513** (0x201) -> the law returns **SHIP**. Actuated
  correctly: the file is written, `reason = "engine law: BUILT -> SHIP"`.

* The bit that was measured and dropped, captured in the same run:

      guard.py:508 measured
          rel               = pkg/geom.py
          packet.truncated  = True
          capped0           = True

* What the law WOULD have ruled on the correct byte: `situation(BUILT=True,
  CAPPED=True)` = **545** (0x221) -> **RAISE_BUDGET**. `loop._rule` already has the
  branch for it and the honest refusal text is already written
  (`loop.py:238-242`: *"a candidate passes, but the search was cut short before it
  could be shown unique — shipping it would be a guess"*). It is unreachable from
  the guard's first pass because `capped` can only ever be set by a wall-clock
  deadline.

* Proof the shipped green is **not** the unique repair — the second green, and the
  fact the cut-short search never reached it (`evidence.py`, full-sight control):

      packet.truncated = False  anchors = 118
      repaired=False refused=True ambiguous=True
      greens found: ['return max(low, high)', 'return ceiling - peak(low, high)']
      reason: AMBIGUOUS: 2 candidates at 2 different lines (10, 15) all pass the
              suite — the tests cannot tell them apart, and one may CANCEL the
              fault rather than repair it. Add one pinning test
              (engine law: BUILT+AMB -> ADD_STATE, never guess)

  So the honest chain is BUILT+CAPPED -> RAISE_BUDGET -> full sight -> BUILT+AMB ->
  ADD_STATE -> refuse. Every link exists in the code. Only the first bit is missing.

### B — S1 again, spread-sample route (independent of the signal filter)

    ./timeout.sh 60  .../python make_fixture2.py 46
    ./timeout.sh 600 .../fluidfix guard fixture2

    [14:32:05] pkg/geom.py: repaired line 62 in 112 suite runs (21.8s):
      - return ceiling + peak(low, high)
      + return ceiling - peak(low, high)
    exit 0

Line 57 (`return min(low * SCALE, high * SCALE)`) does carry a signal token; the
110-of-133 stride sample dropped it. Verified independently that the true repair at
line 57 is green (`second green (true repair at line 57) is green? True`), and that
the shipped program is wrong (`peak(1,5)=1`, `headroom(0,1,5)=-1`). Same
classification, same byte.

### C — S3 FALSE CONFIDENCE, riding on the same defect

The report line the user sees is `repaired line 15 …` with
`reason = "engine law: BUILT -> SHIP"`. The run did not support that claim: it had
measured `capped0=True` in the same function, three statements before the call. The
`--dry-run` channel repeats the claim as a patch to apply. Counted separately only
because a run that ships a *correct* single green under a truncated packet is still
making a claim of uniqueness that the run does not support; A and B are the
harmful instances of it.

## 5. What defended

* **The AMB lane, whenever it can see.** With an untruncated packet the identical
  fixture refuses with an accurate, specific reason naming both lines and warning
  that one may cancel the fault. The proxy `set_amb or len(sites) > 1` did its job;
  the cap simply deleted one of the two sites before it could count it.
* **The escalation stage.** Attempt 7: with the same cap and the same dropped line,
  but *no* green in pass 0, `situation(CAPPED=True, REFUTED=True) -> RAISE_BUDGET`
  fires, the packet is rebuilt at `max_lines=10**9`, and the guard repairs the true
  line. The full-sight machinery is correct and reachable — only an early
  `status="repaired"` return jumps over it.
* **`_is_test_path` / the candidate-file filter.** The tests were never a candidate
  for mutation; the cheapest green (edit the assertion) was never available.
* **`--dry-run` integrity.** The tree was restored byte-exactly; the only damage was
  the proposal's content, not the repo state. No S2 anywhere in this work.
* **The compile pre-check and the `tried` dedup.** Kept the 110-duplicate anchor
  list produced by the stride sample from costing 110 redundant suite runs, and
  rejected syntactically dead candidates for free.

## 6. Verdict

fluidfix did not hold: with the observation packet truncated — by either the signal
filter or the stride sample — the CAPPED bit measured at `guard.py:508` never
reaches `loop.py:217`, so a search that never saw the defective line ships its one
compensating green as `BUILT -> SHIP` (S1, `observation`; byte 513 passed where 545
was measured, SHIP where the law rules RAISE_BUDGET).

---

### Files kept here

    make_fixture.py    builds `fixture/` — signal-filter route (variant 1)
    make_fixture2.py   builds `fixture2/` — spread-sample route (variant 2)
    find_pad.py        the search that found pad=46 for variant 2
    probe_packet.py    proves the two greens and the packet's contents, no guard
    evidence.py        runs guard_once and snapshots guard.py:508 + loop.py:217
                       with sys.settrace (read-only; nothing is patched)
    evidence.out       captured output of the above
    repro.sh           all of it, in order
    timeout.sh         `nice -n 15` + a real timeout (macOS has no coreutils one)
    pristine/geom.py   the correct program, for byte comparison
    before_geom.py     the as-found (broken) defect file from the recorded run
    fixture/, fixture2/, control_fixture/   victim repos, left in their broken state
