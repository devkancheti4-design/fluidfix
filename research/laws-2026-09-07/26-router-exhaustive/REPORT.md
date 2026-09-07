# 26-router-exhaustive

## 1. Target
Verify `route(F1, A1, Fq)` (src/fluidfix/router.py) on all 16^3 inputs against its docstring, explain what F1/A1/Fq concretely are inside fluidfix, and find every call site to establish which routes the body can ever produce.

## 2. Method
Read in full: `src/fluidfix/router.py`, `src/fluidfix/acts.py`, `src/fluidfix/loop.py` (1-60, 255-440), `src/fluidfix/guard.py` (360-430), `src/fluidfix/observers.py` (25-85, 145-170), `src/fluidfix/lanes.py`, `src/fluidfix/cli.py` (415-460), `tests/test_router_law.py`, `tests/test_acts.py`, `tests/test_e2e.py`.

Call-site census: `grep -rn -E "router|route_packed|\broute\b" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=research --exclude-dir=__pycache__ --exclude-dir=dist` and `grep -rn "act_for\|ACTS\|WORKED_EXAMPLE\|mask_of\|kind_of" src/ tests/`.

Scripts written here (all runnable, all via the local timeout wrapper `run.sh`, which is `nice -n 15` plus a perl `alarm` because this machine has no coreutils `timeout`):

| script | output | what it does |
|---|---|---|
| `exhaustive.py` | `exhaustive.out` | all 16^3 inputs vs a hand-written reference; range, identity, bijection, renumbering, composition, high-bit independence, out-of-domain args, act table |
| `reach.py` | `reach.out` | which inputs the body can construct; the loop's filter vs the ranker's |
| `renumber.py` | `renumber.out` | the "wrong on none of 16 renumberings" claim, against fluidfix's own ACTS |
| `live_trace.py` + `fixtures_def.py` | `live_trace.out` | wraps `fluidfix.acts.route` in-process and logs every call during 10 real repairs |
| `cost.py` | `cost.out` | routed vs all-applier candidate counts on the fixtures |
| `precision.py` | `precision.out` | same, on 12 hand-chosen lines including signal-dense ones |
| `corpus.py` | `corpus.out` | same, on all 7,872 lines of fluidfix's own `src/` + `tests/` |
| `order.py` | `order.out` | the observer's kind ordering vs the loop's walk order |

Shipped checks re-run: `run.sh 300 .venv/bin/python -m pytest tests/test_router_law.py tests/test_acts.py -q` and `run.sh 300 .venv/bin/fluidfix selfcheck` (`selfcheck.out`).

Nothing outside this directory was written; no git state was changed.

## 3. Findings

### F1 - the law is exact on all 4,096 inputs, and on five algebraic properties beyond the ones selfcheck pins
```
$ ./run.sh 240 .venv/bin/python exhaustive.py
== R1  all 16^3 inputs vs the docstring reference
agree 4096/4096; disagreements: []
== R2  output is always in 0..15
distinct outputs = [0, 1, ..., 15]  (min=0 max=15)
== R3  identity: route(F1, A1, F1) == A1
holds on 256/256
== R4  bijection: fixing two arguments, the third permutes 0..15
vary F1: True   vary A1: True   vary Fq: True  (all 256 slices each)
== R5  renumbering: adding t to BOTH A1 and the answer, or to F1 and Fq
act renumbering (65536 cases): True
kind renumbering (65536 cases): True
== R6  composition: route(0,o2,route(0,o1,q)) == (q+o1+o2) mod 16
holds on 4096/4096
```
The reference in `exhaustive.py` is written by hand from the docstring (`(Fq + A1 - F1) % 16`); it imports nothing from fluidfix except the law under test.

Algebraically the expression is `15 & ((x>>4) + ((x>>8) - x))` on `x = F1 | A1<<4 | Fq<<8`. Masked to 4 bits, `x>>4` contributes `A1`, `x>>8` contributes `Fq`, `-x` contributes `-F1`; every higher term is a multiple of 16 and vanishes. Sum == `A1 + Fq - F1 (mod 16)`. R4 (bijection in each argument) is the property that carries the safety weight - see F7.

### F2 - "Bits 12-31 cannot influence the result" holds exhaustively, not just on a sample
`tests/test_router_law.py:38` probes this with 10,000 random draws. Checked exhaustively over the whole 12-bit payload:
```
== R7  'Bits 12-31 cannot influence the result' -- exhaustive over payload
4096 payloads x 20 high bits (both int32-positive and sign-extended negative): violations = 0; first = []
== R7b random int32 probe, 200000 draws
route_packed(x) != route_packed(x & 0xFFF) on 0/200000 draws
```

### F3 - F1, A1 and Fq, concretely, inside fluidfix
- **F1** = the fault kind of the **one worked example**: `WORKED_EXAMPLE = (0, 5)` at `src/fluidfix/acts.py:53`. Kind 0 is `"strictness"` (`acts.py:76`): a token containing `<` or `>` with one `=` too many or too few.
- **A1** = the act code that repairs that one example: **5**, which is `ACTS[5] = _flip_strictness` (`acts.py:303`).
- **Fq** = the fault kind of the case at hand - an integer an *observer* put in `Observation.kinds` (`acts.py:60`), walked out of a bitmask by `lanes.py` (`loop.py:283` `mask_of` -> `loop.py:297` `kind_of(EMIT(mask))`).
- **The return value** is an act code: a key into `acts.ACTS`, i.e. which applier function proposes candidate lines.

So the router's whole job in fluidfix is: *given that "a strictness fault is repaired by flipping strictness", what repairs a min/max swap?* Answer `route(0, 5, 8) = 13 = _swap_minmax`.

### F4 - every call site, and the only route the body can produce
| location | call | can it decide anything? |
|---|---|---|
| `src/fluidfix/acts.py:319` (`act_for`) | `route(WORKED_EXAMPLE[0], WORKED_EXAMPLE[1], kind)` | **yes - the only production call** |
| `src/fluidfix/loop.py:299` | `act = act_for(kind)` -> `loop.py:305 candidates(body, act, obs)` | yes, the repair loop |
| `src/fluidfix/acts.py:346` (`register`) | `code = act_for(kind)` -> `ACTS[code] = applier` | yes, at teaching time |
| `src/fluidfix/guard.py:401` | `act_for(k)` for the ranking law's CHEAP bit | no repair outcome; feeds `rank.py` |
| `src/fluidfix/cli.py:436/439/442` | selfcheck, all 4,096 | no - self-verification only |
| `src/fluidfix/__init__.py:22` | re-export | - |
| `tests/test_router_law.py` | all 4,096 | - |

`F1` and `A1` are **frozen module constants**. The body therefore constructs **16 of the 4,096 inputs (0.39%)**, all of the form `route(0, 5, kind)`. Confirmed live by wrapping `fluidfix.acts.route` in-process across ten real repairs:
```
$ ./run.sh 300 .venv/bin/python live_trace.py
k0_strictness          True          6  ['(0,5,1)->6', '(0,5,0)->5', '(0,5,10)->15', '(0,5,3)->8']
                   new line: 'if x > t:'
...
k12_flipped_boolean     True          2  ['(0,5,12)->1']
                   new line: 'DEBUG = False'
out_of_vocab          False          1  []
                   refusal: 'no observation named a kind this vocabulary can repair'
-- every distinct (F1,A1) pair the body produced across all fixtures:
   [(0, 5)]
-- every distinct Fq (fault kind) the body produced: [0, 1, 2, 3, 8, 9, 10, 11, 12]
-- every distinct act produced: [0, 1, 5, 6, 7, 8, 13, 14, 15]
```
All nine shipped fault classes route correctly **and repair end to end** (9/9 fixtures green, one deliberate out-of-vocabulary fixture refuses). The full routing table (`exhaustive.py` R9):

| kind | class | act | applier |
|---|---|---|---|
| 0 | strictness | 5 | `_flip_strictness` |
| 1 | literal-off-by-one | 6 | `_reduce_literal` |
| 2 | swapped-return-operands | 7 | `_swap_return_operands` |
| 3 | flipped-additive | 8 | `_flip_additive` |
| 4,5,6,7 | *unregistered* | 9,10,11,12 | none |
| 8 | minmax-swap | 13 | `_swap_minmax` |
| 9 | flipped-augmented-assign | 14 | `_flip_augmented` |
| 10 | flipped-comparison-direction | 15 | `_flip_comparison` |
| 11 | reversed-minus-operands | 0 | `_reverse_minus_operands` |
| 12 | flipped-boolean | 1 | `_flip_boolean` |
| 13,14,15 | *unregistered* | 2,3,4 | none |

An unrouted act is a silent no-op costing zero suite runs (`acts.py:399-400 if fn is None: return [line]` -> `loop.py:326` NOPROGRESS -> ADVANCE), verified in `reach.out` B6.

### F5 - THE MAIN FINDING: the law is consulted on every candidate set, and its ruling prunes nothing under the shipped observer
The body **does** consult the router (F4) - this is not a "never consulted" law. But the *value* of the ruling is zero as measured today, because the observation it is handed comes from the same regexes the appliers already self-guard on. `observers.py:37` reports **every** kind whose `KINDS` signal regex matches the line; each applier is a no-op on lines outside its own shape. Measured over all 7,872 lines of fluidfix's own `src/` and `tests/`:
```
$ ./run.sh 300 .venv/bin/python corpus.py
files scanned                              44
lines scanned                              7872
lines the mechanical observer signals      2249
lines where MECH prunes anything vs ALL    0

candidates ALL  (no routing law)           5232
candidates MECH (routed, mech observer)    5232
candidates TRUE (routed, one-kind observer)3786

routing saves vs ALL, mechanical observer: 0 / 5232 = 0.0000%
routing saves vs ALL, one-kind observer:   1446 / 5232 = 27.6376%
```
The same result on 12 hand-picked lines, including deliberately signal-dense ones (`precision.out`):
```
return max(hi - 1, lo) if a >= b else min(hi + 1, lo)    [0, 1, 2, 3, 8, 10, 11]    9     9     2
ok = True if n >= 10 else False                          [0, 1, 10, 12]             5     5     1
TOTAL (distinct candidates = suite runs)                                           33    33    13
routing from the MECHANICAL observer saves 0 of 33 candidates (0.0%)
routing from a PRECISE (one-kind) observer saves 20 of 33 candidates (60.6%)
```
Candidate count is the right unit: the loop dedups on `(lineno, candidate)` (`loop.py:332`) and pays exactly one suite run per surviving candidate (`loop.py:355`), and it does **not** stop at the first green - it runs the whole set so `set_amb` can be measured (`loop.py:398-406`). On the fixture set the same holds (`cost.out`: routed 18, all-appliers 18, saved 0).

This is an **observation** finding, not a ruling one: the law rules correctly on the byte it is given; the byte (`obs.kinds`) is simply never more specific than the appliers' own guards.

### F6 - the observer's kind ORDER is discarded before the router sees it, and it is outcome-relevant
`observers.py:54` asks the observer for kinds "**most specific first**", and `acts.py:60` documents `kinds` the same way. `loop.py:283` converts that ordered list to a **bitmask**, and `lanes.py:21` `EMIT(m) = m & -m` then walks it low-bit-first - ascending kind number. The stated ordering is destroyed. It matters because `loop.py:222` ships `greens[0]`, and greens are appended in walk order.
```
$ ./run.sh 300 .venv/bin/python order.py
the loop's walk order is the bitmask's, not the list's:
  obs.kinds=[0, 1, 10]   mask=0x00403  loop walks [0, 1, 10] -> acts [5, 6, 15]
  obs.kinds=[1, 0, 10]   mask=0x00403  loop walks [0, 1, 10] -> acts [5, 6, 15]
  obs.kinds=[10, 1, 0]   mask=0x00403  loop walks [0, 1, 10] -> acts [5, 6, 15]

and the shipped repair follows the walk, not the list:
  obs.kinds=[0, 1, 10]   repaired=True  greens=['    if n >= 10:', '    if n > 9:']  shipped='if n >= 10:'
  obs.kinds=[1, 0, 10]   repaired=True  greens=['    if n >= 10:', '    if n > 9:']  shipped='if n >= 10:'
  obs.kinds=[10, 1, 0]   repaired=True  greens=['    if n >= 10:', '    if n > 9:']  shipped='if n >= 10:'
```
(Fixture: `if n > 10:` where the intended predicate is `n >= 10`. Two greens at one site, from two different candidate sets.) On this fixture the two greens are the same program spelled twice, so no wrong repair occurs - exactly the case `loop.py:213-216` says must not be refused. The defect is that the body asks for information it then throws away.

### F7 - why the bijection (R4) is the load-bearing property for teaching
`register()` (`acts.py:346`) assigns a new class's applier to `ACTS[act_for(kind)]`. Because `route(0, 5, .)` is a bijection on 0..15 (F1/R4), two distinct fault classes can never be handed the same applier slot:
```
== B4  no two distinct fault classes can share an applier
  len({act_for(k) for k in range(16)}) = 16 / 16
```
Seven kind slots are free - `[4, 5, 6, 7, 13, 14, 15]` - and their act codes `[9, 10, 11, 12, 2, 3, 4]` are exactly the seven codes with no applier (`reach.out` B5).

### F8 - the "wrong on none of the 16 renumberings" claim, checked against fluidfix's own act table
```
$ ./run.sh 240 .venv/bin/python renumber.py
renumberings on which the ROUTER is fully right: 16/16
renumberings on which a FROZEN TABLE is fully right: 1/16
NOTE: the router needs A1 in acts.py:53 WORKED_EXAMPLE moved with the vocabulary; router.py itself is untouched. With A1 left at 5 the router is right on:
  1/16 renumberings -- i.e. it degenerates to the frozen table.
```
The claim reproduces (16/16 vs 1/16) on fluidfix's nine registered classes. The invariance lives in **one constant, `acts.py:53`**, not in `router.py`; the docstring's "without touching code" and the README's "the router is never edited" are accurate read that way, and renumbering the worked example alongside the vocabulary is what "one worked example" means. Recorded so the claim is not read as stronger than it is.

### F9 - shipped checks reproduce
```
$ ./run.sh 300 .venv/bin/python -m pytest tests/test_router_law.py tests/test_acts.py -q
29 passed in 3.70s

$ ./run.sh 300 .venv/bin/fluidfix selfcheck
fluidfix 0.14.0
router vs reference, all 4096 (F1,A1,Fq): 4096/4096
identity route(F1,A1,F1)==A1:               256/256
composition route(o2, route(o1, q)):        4096/4096
...
SELFCHECK PASS - 6 laws re-derived
```
`tests/test_router_law.py` pins all 4,096 inputs directly (`test_reference_all_4096`). **No input of this law is unpinned** - unlike the other five laws, whose targets ask for unpinned-input lists.

## 4. Lanes
The router has no named lanes; its "lanes" are its 4,096 inputs and 16 outputs.

**Reached by my work:** all 4,096 inputs (F1, F2), all 16 outputs.

**Reached by the shipped body:** 16 inputs (`F1=0, A1=5, Fq=0..15`) - 0.39% of the domain. Of those, 9 land on an applier and were each exercised end to end by a real repair (F4); 7 (kinds 4,5,6,7,13,14,15 -> acts 9,10,11,12,2,3,4) land on no applier and are silent no-ops.

**Never reached, and what would reach it:**
- Any `F1 != 0` or `A1 != 5`: reachable only by editing `acts.py:53`. Nothing measures the worked example; it is a literal.
- The 7 applier-less acts: reachable by one `register()` call (`acts.py:324`) or a `load_dictionary()` file. `tests/test_teaching.py:49` already exercises kind 4 -> act 9 this way, so the mechanism works; the shipped vocabulary just leaves them empty.
- **Every route the body can ever produce is therefore `route(0, 5, k)` for `k` in {0,1,2,3,8,9,10,11,12} under the shipped vocabulary, plus {4,5,6,7,13,14,15} after teaching.** No third value of `F1`/`A1` exists anywhere in `src/`.

## 5. Potential
- **A one-kind (most-specific) observation would cut candidates - hence suite runs - by 27.6%** on a 7,872-line corpus (1,446 of 5,232, `corpus.out`) and by 60.6% on signal-dense lines (20 of 33, `precision.out`). That is what the router's ruling is *capable* of buying and buys none of today. Caveat, stated plainly: a one-kind observation that names the wrong kind loses the repair; the 27.6% is a cost reduction at a precision the mechanical observer does not have. Whether an LLM observer achieves that precision is **unmeasured**.
- **Honouring the observer's stated "most specific first" order** (F6) costs nothing in suite runs - it only changes which of several equally-green spellings is shipped. Its value is report quality and closeness to the maintainer's own fix; **unmeasured**.
- **The 7 free kind slots** are pure headroom: each new fault class costs one `register()` call and is routed for free by the existing law. What fraction of real defects falls outside the nine shipped classes is **unmeasured** here (see targets 44 and 48).
- **The router's raw decision cost** is four integer ops. The README quotes 1.55 ns/decision from fluid-router2's C verifier; timing is **unmeasured** here.

## 6. Defects

**D1 - observation (latent, ranking-only).** `guard.py:401` calls `act_for(k)` over `obs.kinds` **unfiltered**, while `loop.py:283` filters `0 <= k <= 15`. `pack()` masks each field to 4 bits, so an out-of-range kind silently aliases mod 16 into a real fault class:
```
== B3  a kind the loop DROPS still buys a candidate count in the ranker
  obs.kinds     = [99]   (99 & 15 == 3 -> kind 3 = 'flipped-additive')
  act_for(99)   = 8  -> applier _flip_additive
  guard CHEAP n = 1  -> cheap = True
  loop kinds    = []  <- the loop tries NOTHING
  guard SIGNALED bit = bool(obs.kinds) = True  <- claims a signal the loop cannot act on
```
The ranking law is handed CHEAP and SIGNALED bits for a class the repair loop will never try, so it can promote an observation that cannot produce a single candidate. **No wrong repair is possible** - the loop does nothing with the kind. The masking is the kernel's documented domain (`route` is mod 16 by construction); the defect is the missing `0 <= k <= 15` filter at `guard.py:401`, i.e. a **mismeasured bit**, not a ruling. Reachability: the `MechanicalObserver` only emits keys of `KINDS`, and the `ClaudeObserver`'s JSON schema bounds kinds to 0..15 (`observers.py:71`) - but `observers.py:161` does not re-check that bound, and `Observation` is public API, so a custom observer or a schema-violating response reaches it.

**D2 - observation (F6).** The observer contract asks for kinds "most specific first" (`observers.py:54`, `acts.py:60`); `loop.py:283` `mask_of` discards the order, and the ruling that ships (`loop.py:222` `greens[0]`) follows ascending kind number instead. Evidence in F6 / `order.out`. Classified as observation: the ordering *is* measured, then dropped before the law is consulted. Not a wrong repair on the fixture built (the two greens are the same program spelled twice), but the mechanism is real. The discarded information is the *sequence* of Fq values - the router itself only ever sees one kind at a time, so this is not a router lane the body fails to consult.

**D3 - wording (minor).** `acts.py:91` and `acts.py:308` describe kinds 4..7 / acts 9..12 as *the* free slots. Kinds 13, 14, 15 are also unregistered and route to free acts 2, 3, 4; `register(13, ...)` succeeds with no clobber warning because `SHIPPED_KINDS` does not contain them, yet the docstring at `acts.py:328` steers users to 4..7 only. `tests/test_acts.py:17` asserts only 4..7 stay free. Nothing is wrong; the comment under-reports the headroom by three slots.

**No ruling defect found.** On all 4,096 inputs the law equals `(Fq + A1 - F1) mod 16`, its own stated specification.

**Adjacent, out of my scope, flagged for target 04:** two greens at one site arriving from *different candidate sets* set neither `set_amb` (which counts greens within one set only, `loop.py:400`) nor `len(sites) > 1`, so `AMB` is False and `greens[0]` ships. `loop.py:213-216` says this is intended for two spellings of one program; whether two genuinely different programs can reach that shape at one site is **unmeasured** here.

## 7. Verdict
The fluid-router law is exact on all 4,096 inputs and on identity, bijection, composition, renumbering and high-bit independence; the body does consult it, on every candidate set, but only ever at the single frozen input family `route(0, 5, kind)` (16 of 4,096 inputs), and its ruling prunes 0 of 5,232 candidates over a 7,872-line corpus because the observation it is handed is computed from the same regexes the appliers already self-guard on - a precise one-kind observation would make the same ruling worth 27.6%.
