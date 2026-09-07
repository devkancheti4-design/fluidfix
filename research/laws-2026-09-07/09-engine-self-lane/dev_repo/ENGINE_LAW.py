"""THE ENGINE LAW — one controller for four jobs.

AUTHORED BY THE SPHERE (model-k-d) on 2026-08-17 from 22 measured events, in
2.9 seconds. It decides what to do next for WRITE_CODE, ANSWER, DEBUG and
REVIEW_PR with a single function, because it reads the SITUATION of the work
and never its content. Measured: 0 of 256 observations rule differently across
the four jobs.

    exact on all 22 measured events
    all 8 acts reachable          AUTHOR_SUCCESSOR fires on 60 of 1024
    BUILT+AMB coherent            2 acts, not the 7 that broke the prior law
    job invariance                0 of 256 differ across jobs

WORD: EXACT-ON-EXAMPLES(22). The engine's own note is
"forced +-join — exact, minimality not proved", so minimality is NOT claimed.
Its rulings on the 1002 unmeasured situations are ITS decisions, printed by
self_report(), and unclaimed until measured.

HEAD TO HEAD, same data, 8 events withheld from both sides:
    sphere's law 6/8      Opus 5's hand-written rule 5/8
Both were exact on the 14 supplied. On that smaller set the sphere authored in
0.0s at size 1 with the note "minimal in D∩I" — a genuine minimality claim.

PROVENANCE. The LAW is the sphere's, verbatim. The supplier contributed the
situation encoding, the act numbering, the measured events, the primitives,
and this wrapper. Nothing here was hand-tuned into the expression.
"""

# ------------------------------------------------------------- THE LAW ----
# Authored, verbatim. Do not edit; re-author from more events instead.
# In terms of the supplied primitives it reads:
#
#     act = (4 & ntzb(x - 7)) + ntzb(x + (x & 128))
#
# where ntzb(v) = index of the lowest set bit of (v & 254), i.e. WHICH
# blocking observation came first. The two shifted calls are how it resolved
# a contradiction in the evidence: x + (x & 128) carries the SELF bit OUT of
# the blocker field, so SELF stops blocking when the work already succeeded;
# 4 & ntzb(x - 7) adds 4, lifting NOTWIN's 3 to AUTHOR_SUCCESSOR's 7.
LAW = '((4 & ((((((((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) + ((((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) - ((((((((((x - 7)) & 254)) & (0 - ((((x - 7)) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) >> 4)) & 252645135))) & 7)) + ((((((((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) + ((((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) & 858993459) + ((((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) - ((((((((((x + (x & 128))) & 254)) & (0 - ((((x + (x & 128))) & 254))))) - 1)) >> 1) & 1431655765))) >> 2) & 858993459))) >> 4)) & 252645135))) & 7))'

# ------------------------------------------------- SITUATION ENCODING ------
BITS = ['BUILT', 'AMB', 'UNREAD', 'NOTWIN', 'HIDDEN', 'CAPPED', 'REFUTED', 'SELF']

JOBS = ['WRITE_CODE', 'ANSWER', 'DEBUG', 'REVIEW_PR']                       # bits 8-9

# ACT[i] is the response to BITS[i]. That correspondence is deliberate: an
# arbitrary numbering turns the natural rule into a permutation, whose compact
# form needs a variable shift this grammar does not have. Encoding faults are
# supply faults.
ACTS = ['SHIP', 'ADD_STATE', 'ADD_MATERIAL', 'RESHAPE', 'CHANGE_GRANULARITY', 'RAISE_BUDGET', 'HARVEST_COUNTEREXAMPLE', 'AUTHOR_SUCCESSOR']


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def situation(job, **obs):
    """Pack observations into the law's input. Observations only, never
    opinions — an invented label is what made an earlier law abstain."""
    return (sum(1 << BITS.index(k) for k, on in obs.items() if on)
            | (JOBS.index(job) << 8))


def decide(sit):
    """The sphere's ruling. Pure; reads the state of the work, never the
    content — which is why one law governs all four jobs."""
    return s32(eval(LAW, {"__builtins__": {}}, {"x": s32(sit)})) % 8


# ------------------------------------------------------------- THE LOOP ----
def run(worker, jobs, observe, apply_act, rounds=64):
    """worker(job)                 -> result    any engine: a compiler, a
                                                 test runner, a model, a search
       observe(job, result)        -> situation what actually happened
       apply_act(act, job, result) -> job|None  perform the ruling

    Every decision is the law's; the host only executes. When the job being
    worked on IS the worker (SELF), the same loop authors its successor —
    that is the recursion, and it needs no special case here."""
    queue, ledger = list(jobs), []
    for rnd in range(1, rounds + 1):
        if not queue:
            break
        progressed = False
        for job in list(queue):
            result = worker(job)
            act = ACTS[decide(observe(job, result))]
            ledger.append((rnd, getattr(job, "name", str(job)[:40]), act))
            nxt = apply_act(act, job, result)
            if act == "SHIP":
                queue.remove(job); progressed = True
            elif nxt is None:
                queue.remove(job)
            elif nxt is not job:
                queue[queue.index(job)] = nxt; progressed = True
        if not progressed:
            break                    # honest stop: no ruling changed anything
    return ledger


# --------------------------------------------------- THE MEASURED EVENTS --
# job, observations, act, what happened. Every one occurred on 2026-08-17.
EVENTS = [
    ('WRITE_CODE', {'BUILT': 1}, 0,
     'certificate self-test 8/8 -> shipped                     [certificate run]'),
    ('WRITE_CODE', {'UNREAD': 1}, 2,
     '>>4 absent: bottom 10.97s -> supplied: 0.01s, 38 evals   [live probe]'),
    ('WRITE_CODE', {'CAPPED': 1}, 5,
     'size ladder exhausted on clean rows -> deepened the cap   [duel ladder]'),
    ('WRITE_CODE', {'NOTWIN': 1}, 3,
     "intent 'mix' has no LIN: the shape was unreachable in it  [sqr targets]"),
    ('ANSWER', {'BUILT': 1}, 0,
     'answer passed its own check -> delivered                  [liveness reply]'),
    ('ANSWER', {'UNREAD': 1}, 2,
     "'which seeds work better as shield': no measurement existed, ran one"),
    ('ANSWER', {'AMB': 1}, 1,
     'a question with two readings: the missing variable was supplied'),
    ('DEBUG', {'REFUTED': 1}, 6,
     'audit refuted verify_witness AMB branch -> became a test  [audit verdict]'),
    ('DEBUG', {'HIDDEN': 1}, 4,
     '65536-row authoring vs block-complete: same partition,    [duel2/duel3] different scale -> re-recorded coarser'),
    ('DEBUG', {'UNREAD': 1}, 2,
     'shift family absent again in the duel -> supplied         [duel_supply]'),
    ('DEBUG', {'CAPPED': 1}, 5,
     '5GB ceiling on clean rows -> raised, then isolated        [tight/tight3]'),
    ('REVIEW_PR', {'BUILT': 1}, 0,
     '94/94 independent re-derivations, 0 failures -> shipped   [verify_all]'),
    ('REVIEW_PR', {'REFUTED': 1}, 6,
     '2 audit findings survived refutation -> became corrections [audit]'),
    ('REVIEW_PR', {'AMB': 1}, 1,
     'rows mapping one input to two outputs -> resolve first     [certify]'),
    ('WRITE_CODE', {'BUILT': 1, 'REFUTED': 1}, 6,
     '0.02s form BUILT, full-domain check REFUTED it (16384 wrong) -> holdout gate'),
    ('DEBUG', {'CAPPED': 1, 'UNREAD': 1}, 2,
     "5GB ceiling while binary '*' was the wrong material -> per-task operators"),
    ('DEBUG', {'BUILT': 1, 'AMB': 1}, 1,
     'certify BUILT a verdict on rows carrying one input twice -> resolve first'),
    ('REVIEW_PR', {'SELF': 1, 'BUILT': 1}, 0,
     "the certificate's own self-test passed and it shipped     [8/8]"),
    ('REVIEW_PR', {'SELF': 1, 'REFUTED': 1}, 6,
     "the audit refuted verify_witness, the module's OWN checker [audit]"),
    ('DEBUG', {'SELF': 1, 'CAPPED': 1}, 5,
     'the harness hit its own 5GB ceiling -> raised to 6GB       [tight3]'),
    ('DEBUG', {'SELF': 1, 'UNREAD': 1}, 2,
     'the harness lacked the shift primitives it had to supply   [duel_supply]'),
    ('WRITE_CODE', {'SELF': 1, 'NOTWIN': 1}, 7,
     'Law-C exists but not in a form covering four jobs -> AUTHOR THIS SUCCESSOR'),
]


def self_report():
    import collections
    print("SUPPLIED — the %d measured events:" % len(EVENTS))
    bad = 0
    for j, o, a, why in EVENTS:
        got = decide(situation(j, **o))
        bad += got != a
        print("  %-10s %-14s -> %-22s %s"
              % (j, "+".join(o), ACTS[got], why[:46]))
    print("\n  exact on all %d measured events: %s" % (len(EVENTS), not bad))

    cov = collections.Counter(decide(x) for x in range(1024))
    print("\n  ACT COVERAGE over all 1024 situations")
    for i, a in enumerate(ACTS):
        print("    %-24s %4d" % (a, cov.get(i, 0)))
    dead = [a for i, a in enumerate(ACTS) if not cov.get(i, 0)]
    print("    acts that never fire: %s" % (dead or "NONE"))

    diff = sum(1 for s in range(256)
               if len({decide(s | (j << 8)) for j in range(4)}) > 1)
    print("\n  JOB INVARIANCE: %d of 256 observations rule differently "
          "across the four jobs" % diff)

    print("\n  its rulings where nothing was measured (its call, not ours):")
    for s, name in ((128, "SELF alone"), (131, "SELF+BUILT+AMB"),
                    (255, "every fault set"), (0, "nothing set"),
                    (6, "AMB+UNREAD"), (48, "HIDDEN+CAPPED")):
        print("    %-18s -> %s" % (name, ACTS[decide(s)]))


if __name__ == "__main__":
    self_report()
