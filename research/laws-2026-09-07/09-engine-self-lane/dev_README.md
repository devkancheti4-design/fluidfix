# dev — the engine law

**Private.** Working repository for the four-job controller authored by the
sphere (model-k-d) on 2026-08-17.

```
act = (4 & ntzb(x - 7))  +  ntzb(x + (x & 128))

ntzb(v) = index of the lowest set bit of (v & 254)
        = which blocking observation came first
```

`sha256 48bf50bff36a2cc9` · 1,555 characters · authored in 2.9 s from 22
measured events · appears verbatim in the authoring log · the only arithmetic
form in `ENGINE_LAW.py`.

## One controller, four jobs

`WRITE_CODE` · `ANSWER` · `DEBUG` · `REVIEW_PR`

| bit | observation | act |
|---|---|---|
| 0 | BUILT — produced an artefact that passed its own check | SHIP |
| 1 | AMB — one input carries two outputs | ADD_STATE |
| 2 | UNREAD — no tool or fact reads the needed field | ADD_MATERIAL |
| 3 | NOTWIN — exists, but not in the form needed | RESHAPE |
| 4 | HIDDEN — fine records disagree, coarse agree | CHANGE_GRANULARITY |
| 5 | CAPPED — clean input, budget exhausted | RAISE_BUDGET |
| 6 | REFUTED — an independent checker rejected it | HARVEST_COUNTEREXAMPLE |
| 7 | SELF — the job *is* the worker | AUTHOR_SUCCESSOR |

The job lives in bits 8–9 and the law ignores them entirely. That is where the
generalisation comes from: it governs four jobs *because it never looks at
which one it is in*.

## Every test

```
exact on the events it was authored from      22 / 22
acts that never fire                          NONE  (AUTHOR_SUCCESSOR: 60/1024)
job invariance                                0 of 256
BUILT+AMB, the region that broke the prior law 2 acts (prior law: 7)
18 real failures from the authoring session   18 / 18, 11 never shown to it
sealed head-to-head, 8 withheld events        law 6/8   Opus 5 5/8
driving a real worker, 8 starved tasks        8/8, 0 wasted
  ablation: always SHIP                       2/8
  ablation: always RAISE_BUDGET               0/8
  ablation: bit-reversed law                  0/8, 59 wasted
repairing real Python (worker = interpreter)  5/6  vs 1/6, 0/6
closed loop, no human in the cycle            10/10, 3 successors, 0 regressions
a different domain, 10 observations/10 acts   23/28 unseen, p = 5.9e-19
writing code from 4-6 examples, judged on 64  10/10   (Opus 5: 10/10)
all three jobs, brain + frontier body         16/16 both; 83% fewer tokens
cost                                          2.43 us, 411,602/sec, 0 tokens
```

`python tests/engine_all_tests.py` re-runs the first eight in one pass.

## Any form of code

`tests/anyform.py` swaps the body and changes nothing else. The int32 engine is
replaced by a general Python writer over strings, lists and dicts; the law is
byte-identical. Starved at tier 0 / size 1, judged on held-out inputs:

```
reverse a string        ADD_M->SHIP                s[::-1]
count words             ADD_M->..->RAISE           len(s.split())
unique words in order   ADD_M->..->RAISE           list(dict.fromkeys(s.split()))
words by length         ADD_M->..->CHANG           sorted(s.split(), key=len)
title-case the words    ADD_M->..->CHANG           [w.capitalize() for w in s.split()]
sorted unique chars     ADD_M->..->CHANG           list(dict.fromkeys(sorted(s)))
run-length encode       ADD_M->ADD_M->ADD_M->SHIP  __rle(s)
                                              10 / 10 held-out exact
```

So the grammar limit in the write-code test belongs to the **engine**, not the
law. The moves are still supplied — the law finds the composition and the
escalation, it does not invent primitives.

## Clean data is not sufficient

`tests/cleanbits.py` enumerates it. Only **2 of the law's 8 observations
describe the data** — AMB and HIDDEN. The other six survive perfectly clean
data. Of the 256 observations, 64 are data-clean, and on those the law says
SHIP on **4 — 6.2%**; on the other 93.8% its own ruling is *not done yet*.

Three of the 22 events it was authored from say so outright:

```
WRITE_CODE  CAPPED         -> RAISE_BUDGET   "size ladder exhausted on clean rows"
DEBUG       CAPPED         -> RAISE_BUDGET   "5GB ceiling on clean rows"
WRITE_CODE  BUILT+REFUTED  -> HARVEST        built in 0.02s, then 16384 wrong
```

`CAPPED` is defined as *"clean input, budget exhausted."* If clean data were
sufficient that bit would be dead code.

And `anyform.py` is its own demonstration: it scored **7/10 then 10/10 on
byte-identical data**. What moved was one act's implementation — the law had
been ruling `CHANGE_GRANULARITY` correctly the whole time while the harness
re-added rows it already held.

## What it is not

- `EXACT-ON-EXAMPLES(22)`, **not** minimal — the engine's own note reads
  `forced +-join — exact, minimality not proved`.
- Its rulings on the other 1,002 situations are its decisions, **unclaimed
  until measured**.
- It contributes nothing to bugs that need to know what the code was *for* —
  a wrong operator, an off-by-one, a missing return. Measured at ~17% of a
  realistic corpus.
- Every "law failed" result in this repository's history turned out to be a
  supply fault: a missing shift family, a De Bruijn hash that was not an
  index, a median split, a popcount template missing its horizontal sum, a
  sampling hole, `replace(..., 1)`, and constants excluded from "material".

## What is under test here

**Not the sphere.** The sphere's work ended on 2026-08-17: 2.9 seconds, 22
events, one expression. Everything in `tests/` measures the ARTEFACT it
authored — a law that runs with no engine behind it, in 2.43 us, for 0 tokens.

That split is visible in the imports:

```
test only the authored law     anyform.py  cleanbits.py  engine_all_tests.py
  (no engine, no sphere)       universal.py  mybugs.py

call the engine as a BODY      bolt2.py  closedloop.py  debugger.py  final.py
  (the law still decides)      law_h2h.py  newdomain.py  sweep_engine.py
                               writecode.py
```

`anyform.py` contains zero references to the engine. Its 10/10 is the law
alone, driving a body the sphere never saw, on tasks in a form the sphere
cannot express. The authored thing outlives the authoring.

## Not included

The authoring engine is private and is **not** in this repository. What ships
is what it wrote.

Public releases derived from this work:
[edgub](https://github.com/devkancheti4-design/edgub) (the debugger policy) and
[edgub-agent](https://github.com/devkancheti4-design/edgub-agent) (the hands).

## The generalisation proof lives here, not in edgub

`proof/generalisation/` is the ENGINE law's result and was moved out of the
public edgub repository, where it did not belong and could not even run — its
runner imports `ENGINE_LAW`, which that repo does not ship.

Twenty functions composed by a seeded generator, six examples each, judged on
twenty held-out inputs neither side saw:

```
                       exact    abstained (⊥)    WRONG     tokens
law, fair supply       19/20          1            0            0
opus 5, four agents    19/20          0            1      178,544
```

Proved generalised rather than recalled by four checks including a negative
control — fed a different program's examples, 0 of 20 returned the original and
20 of 20 returned the empty space. Method, token distribution, and the account
of the harness mistake that first scored it 17/20:
[proof/generalisation/GENERALISATION.md](proof/generalisation/GENERALISATION.md)

`proof/closed_loop.py` also moved here: it consults this law to rule on the
debugger's own contradictions, which is this law's job, not the debugger's.
