# Does the law generalise, or does it recall?

A frontier model repairing `nth` in **toolz** is recalling `nth`. toolz is a
famous public repository; it is in the training data. That measures memory.

So this test uses code that exists nowhere: twenty functions composed by a
seeded generator from templates, with randomly chosen variable names and
constants. Both sides get **the same six (input, output) examples** and the
broken source, and both are judged on **twenty held-out inputs neither was
shown**.

## Result

```
                       exact    abstained (⊥)    WRONG     tokens
law, fair supply       19/20          1            0            0
opus 5, four agents    19/20          0            1      178,544
```

Tied on coverage. They missed the **same** program, P10. The law returned ⊥.
Opus 5 returned `x * 2 % 19` — which fits all six examples exactly and is wrong
on held-out. On a real repository that difference is the whole difference: a
plausible wrong patch is worse than "not in my space".

Every act was chosen by `ENGINE_LAW.decide`. Eighteen of twenty shipped on the
first pass; two needed the law to widen its own material:

```
P02  ADD_MATERIAL x3 -> SHIP      needed the constant 7   (numeric tier)
P03  ADD_MATERIAL   -> SHIP       needed the constant 4   (it was already in the function)
P04  ADD_STATE                    the six examples did not determine it
P10  ADD_M x3 -> RAISE_BUDGET     still ⊥ — needs statement insertion
```

## Proof that the 19 were generalised, not looked up

A lookup table passes none of these four.

**1. The inputs searched and the inputs judged are disjoint.**

```
examples given to both sides : [0, 3, 7, 12, 25, 41]
probes the law chose itself  : [14, 16, 18, 20, 22, 24, 26, 27, 29, 30, ...]
held-out, used only to judge : [1, 2, 4, 5, 6, 8, 9, 10, 11, 13, 15, ...]
examples ∩ held-out : empty        probes ∩ held-out : empty
```

**2. The shipped program is behaviourally identical to the original over all
46 inputs**, not just the six it was given — `19 of 19` shipped. It did not fit
the data, it recovered the function.

**3. The programs do not exist anywhere to be recalled.** `corpus.py` composes
them from templates with a fixed seed. No names, no docstrings, no provenance.

**4. Negative control — feed it lies.** Same broken source, six examples taken
from a *different* program. If the answers were recalled, corrupting the data
would change nothing.

```
returned the original anyway (would prove lookup) :  0 of 20
returned a fit to the corrupted data              :  0 of 20
returned the empty space                          : 20 of 20
```

Zero. The answer tracks the data, not the program.

## Token distribution — the whole truth

```
OPUS 5 ARM, four independent agents
   P00-P04    58,628        P05-P09    39,452
   P10-P14    38,653        P15-P19    41,811
   TOTAL     178,544  =  8,927 per program

LAW ARM     0 tokens.  Not "few" — zero. No model is called at any point.
            It spends candidate programs instead: 2,415 total, 120 per program.
```

**What the zero does mean.** At decision time the law calls nothing.
`decide()` is arithmetic on one integer, 2.43 µs. The search is local
execution. No API, no network, no key, no per-run cost.

**What it does not mean.** The law was authored once, by the engine, from 22
measured events — that is not free, it is already paid. A human wrote the
harness it drives. What is zero is the *marginal* cost of every subsequent
decision.

**The honest comparison.** 178,544 tokens bought 19 correct answers and one
confident wrong one. 0 tokens bought 19 correct answers and one abstention.

## My mistake, and it was large

**The first version of this test scored the law 17/20 and I reported it as a
loss.** It was not the law. It was my harness, and the repository owner was
right to challenge it. Three faults:

- **I never called `decide()`.** One fixed pass over a hard-coded edit set,
  labelled "law" — no acts, no escalation, no second look. Meanwhile the model
  arm had a Python interpreter, seven tool calls and ~45,000 tokens of
  reasoning per batch. That is not a comparison, it is a handicap.
- **I withheld material that was sitting in plain sight.** P03 needed the
  constant `4`. `4` was already in the function. Given the function's own
  constants, the law found it in one `ADD_MATERIAL` and shipped. P02 needed
  `7`; three escalations to the numeric tier and it shipped. Opus 5 solved
  that one by hand algebra — the law simply was not allowed to look.
- **I leaked the judging inputs into the search.** Candidate behaviours were
  separated by evaluating them on the held-out inputs. The answers were never
  used, but the model was never given those inputs at all. Closed by giving the
  law its own probe set, disjoint from the judge. The score did not move.

This is the same fault recorded throughout this project's history: every time
the law appeared to lose, the supply was mine and it was wrong. Operators
missing, a constant missing, an act implemented as a no-op, a search handed a
space that could not contain the answer. It has not once been the law.

## Reproduce

```bash
python corpus.py corpus.json        # regenerate the 20 programs (seeded)
python arm_law2.py corpus.json law3_res.json
python proof.py                     # checks 1-3
python control.py                   # check 4, the negative control
python score.py corpus.json out.json ans_0.json ans_1.json ans_2.json ans_3.json
```

`task_0.md` … `task_3.md` are exactly what the four agents were shown — broken
source and six examples, nothing else. `ans_*.json` are exactly what they
returned.

## Limits

- Twenty programs from ten templates. Not a broad benchmark.
- The bugs were generated from the same edit classes the law searches, which
  favours the law. It still tied rather than won.
- The negative control is bounded at tier 0, one edit — the setting that
  answered 18 of 20 in the real run. Stated, not hidden.
- This measures repair-from-examples. It says nothing about bugs whose fix
  depends on knowing what the code is *for*.
