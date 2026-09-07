# Prompt: author the PAIR law (when to attempt more than one edit)

Author a branchless kernel that decides, when a single-edit search has failed,
whether to attempt MORE THAN ONE simultaneous edit — and if so, in what form.

    input   one byte of observations, all mechanically measurable after a
            completed single-edit search
    output  priority 0..7, lower is attempted first

## Why this is dangerous, and what the law must protect against

Measured 2026-09-04 on Unity-shaped gameplay logic. A sign flip in
`ProjectOnPlane` (`v - n*d` -> `v + n*d`) admitted TWO passing repairs:

    line 32   restore the sign          <- the real fix
    line 11   break Vec3's operator+    <- makes the two faults CANCEL

Both pass the suite. The second corrupts vector addition everywhere else in
the program. Single-edit search only avoided shipping it because the engine
law's AMB lane refuses when candidates at two different lines both pass.

**A pair search inverts that protection.** It goes looking for combinations
that are only green jointly — which is the exact shape of two bugs that
cancel. A naive implementation does not merely risk the compensating repair;
it is a machine for finding them. Any law authored here must treat
"green only in combination" as a SUSPICION, never as a success.

## The other constraint is cost

Measured on Box2D's `contact_solver.c`: a single-edit search tried 1,063
candidates before refusing, at 3.5s per candidate.

    single-edit   1,063 candidates      ~1 hour
    naive pairs   564,453 combinations  ~23 days of continuous building

So the law cannot simply say "try pairs". It must rule on whether a pair
search is warranted at all, and prefer any structure that is linear rather
than quadratic.

## The observation byte

    bit  name          meaning (measurable after a single-edit search)
      0  EXHAUSTED     every single-edit candidate was tried and rejected
      1  PARTIAL       some single edit strictly REDUCED the failing-test
                       count without reaching green
      2  DISJOINT      the failing tests partition into groups touching
                       disjoint code sites
      3  COUPLED       every failing test touches the same site
      4  CHEAP         the candidate space is small enough that pairs are
                       affordable under the remaining budget
      5  TAUGHT        the classes involved were taught from worked
                       examples, not guessed at
      6  CANCELING     a candidate pair is green JOINTLY while each member
                       individually leaves the suite red AND does not reduce
                       the failing-test count
      7  CAPPED        clean inputs, but the budget is already spent

## The structural requirements

    R1  A pair is never attempted while any single edit remains untried.
        EXHAUSTED gates everything: cheaper evidence first, always.

    R2  DISJOINT dominates. When the failing tests partition into independent
        groups, the situation is N separate single-bug repairs, not one
        combinatorial one — linear, not quadratic. A law that reaches for
        pairs while a partition exists has chosen the expensive answer to the
        wrong question.

    R3  CANCELING is a VETO, not a weak signal. A pair that is green only in
        combination, whose members each make nothing better alone, must never
        rank as a repair whatever else is true of it. Two bugs that cancel
        satisfy exactly this description; so does nothing else we have
        measured.

    R4  PARTIAL is the discriminator that makes a genuine multi-bug case
        distinguishable from a compensating pair. In a real two-bug program,
        fixing either bug alone REDUCES the number of failing tests. In a
        compensating pair, fixing either alone leaves the count equal or
        worse. Rank accordingly.

    R5  Without CHEAP, a pair search is refused rather than started. Refusing
        with a reason beats a search that cannot finish.

    R6  Deterministic, branchless, no data-dependent loops, no tables.
        Verifiable exhaustively over all 256 inputs.

## The incidents this law must settle

1. Unity `ProjectOnPlane`. EXHAUSTED is false (a single edit does repair it),
   and a candidate pair is CANCELING.
   REQUIRED: never reaches a pair search; CANCELING ranks last.

2. Box2D `contact_solver.c`. EXHAUSTED true, CHEAP false (1,063 candidates),
   PARTIAL false, DISJOINT false.
   REQUIRED: refuses to start a pair search, and says the budget is why.

3. A genuine two-bug program: two independent faults, each with its own
   failing test, each single fix reducing the failure count.
   EXHAUSTED true, PARTIAL true, DISJOINT true.
   REQUIRED: ranks the PARTITION path first — repair them one at a time.

4. Two coupled faults on one code path, both taught, small candidate space.
   EXHAUSTED true, PARTIAL true, COUPLED true, CHEAP true, CANCELING false.
   REQUIRED: this is the ONLY situation in which a pair search ranks first.

5. Nothing observed at all — no exhaustion, no partial progress.
   REQUIRED: the law must not invent a reason to search. Every
   evidence-free input lands in the same low-priority class.

## Deliverables

- `pair.c`: the kernel, same shape as `rank.c` and `sight.c` — evidence lanes
  folded into a sum, one EMIT, priority from the low bit.
- A one-paragraph derivation of why R1, R2 and R3 hold structurally rather
  than by case analysis.
- An exhaustive self-check over all 256 inputs asserting R1-R5 and the five
  incidents above.

Encode no filename, no repository, and no fault class. The law reads the
SITUATION of the search, never the content of the code.

## A note on what this law does NOT decide

Whether an accepted repair SHIPS remains the engine law's ruling
(BUILT / AMB / CAPPED). This law only decides what to attempt next when one
edit was not enough. If a pair is found and accepted, it faces the same
AMB test as any single candidate — and two pairs at different sites are two
outputs for one input, exactly as before.
