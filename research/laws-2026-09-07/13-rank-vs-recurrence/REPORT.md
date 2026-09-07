# 13-rank-vs-recurrence

## 1. Target

Measured fault-class recurrence in the Box2D and cglm histories versus the ranking law's lane
order: would ordering by recurrence save suite runs, and is that the ranking law's business or a
bit it lacks?

## 2. Method

Read (no edits): `src/fluidfix/rank.py`, `src/fluidfix/loop.py` (lines 255-439),
`src/fluidfix/guard.py` (`rank_observations`, lines 340-428, and the budget/escalation path,
lines 500-600), `src/fluidfix/lanes.py`, `src/fluidfix/acts.py` (`KINDS`, `Observation`),
`src/fluidfix/hotspots.py` (`bugfix_churn`), `src/fluidfix/cli.py` (lines 478-497).

Scripts in this directory, all rerunnable with
`/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python <script>`:

| script | what it does | output |
| --- | --- | --- |
| `scan_history.py` | read-only `git log -p -U0` over the shared Box2D/cglm clones; labels one-line fix commits; replays `loop.repair`'s candidate stream on the defect line | `scan_output.txt`, `scan_results.json` |
| `scan_pairs.py` | same, widened to every paired `-`/`+` line inside fix commits | `pairs_output.txt`, `pairs_results.json`, `offbyone_increments.txt` |
| `dedupe.py` | de-duplicates `(repo, old, new)`, excludes version bumps, recomputes the order comparison | `dedupe_output.txt`, `rerun_dedupe.txt` |
| `exhaustive_check.py` | 2-kind Python fixture, both kind orders, real suite runs | `exhaustive_output.txt` |
| **`order_effect.py`** | new: winner-first / winner-last / reversed, with and without a wall-clock deadline, on two fixtures | `order_effect_output.txt` |
| **`order_discarded.py`** | new: all 720 permutations of a 6-kind line through `mask_of`; 5 permutations run end to end; deadline case repeated 5x per order | `order_discarded_output.txt` |
| **`rank_side.py`** | new: pure enumeration of `rank.py` - class identity, lane budget, reachable situations | `rank_side_output.txt` |
| **`cheap_channel.py`** | new: over real history lines, does kind order alone flip the CHEAP bit | `cheap_channel_output.txt` |

Repos were read in place with read-only `git log`; nothing was copied, built, checked out or
mutated. Suite-running scripts run a one-test pytest fixture in a temp dir under this directory
with `FLUIDFIX_CONFIRM=0`. Note: `timeout(1)` does not exist on this machine
(`which timeout` -> not found), so runs were wrapped as
`nice -n 15 perl -e 'alarm 300; exec @ARGV' ...` instead of `timeout 300`.

## 3. Findings

### F1. The body cannot represent a class order at all - `obs.kinds` order is discarded

`loop.py:283` turns the observation's kind list into a bitmask, and `lanes.EMIT` takes the lowest
live bit. A bitmask is a set: the order is gone before the first candidate is generated.

```
loop.py:283   mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
loop.py:297   kind = kind_of(EMIT(mask))
lanes.py:20   def EMIT(m): return m & (-m)          # lowest live bit
```

`nice -n 15 perl -e 'alarm 300; exec @ARGV' .venv/bin/python order_discarded.py`:

```
Part 0  mask_of over all 720 permutations of [0, 1, 2, 3, 10, 11]: 1 distinct mask(s) -> {3087}
        (one mask => the order in obs.kinds is not representable)

Part 1  acts_tried per permutation (of 720 possible, 5 run end to end)
   kinds=[0, 1, 2, 3, 10, 11] -> acts_tried=[5, 6, 7, 8, 15] suite_runs=7 repaired=True
   kinds=[2, 0, 1, 3, 10, 11] -> acts_tried=[5, 6, 7, 8, 15] suite_runs=7 repaired=True
   kinds=[10, 0, 1, 2, 3, 11] -> acts_tried=[5, 6, 7, 8, 15] suite_runs=7 repaired=True
   kinds=[11, 10, 3, 2, 1, 0] -> acts_tried=[5, 6, 7, 8, 15] suite_runs=7 repaired=True
   distinct (acts_tried, suite_runs, repaired, new_line) outcomes: 1
```

The class order is therefore always ascending kind id - an artifact of how `acts.KINDS` is
numbered, not a ruling by any law. `acts.py:60` documents `kinds` as "most specific first"; the
search never reads that.

### F2. Class order cannot save a suite run, because the loop does not stop at the first green

`loop.py:284-419` finishes the whole candidate set for a kind, then walks to the next kind, then
to the next observation. It exits early only on AMB (`loop.py:415`) or a wall-clock deadline
(`loop.py:269, 285`). The stated reason is at `loop.py:287-290`: "a lone green with the set
unfinished is an UNPROVEN-unique repair". So a completed search costs the same number of suite
runs whatever order the classes are in.

`nice -n 15 perl -e 'alarm 300; exec @ARGV' .venv/bin/python order_effect.py`:

```
================ fixture 'cmp': 'if x >= t:'
  kinds on the line: [(0, 'strictness'), (10, 'flipped-comparison-direction')]
  --- A: no deadline ---
   loop order    order=[0, 10] repaired=True suite_runs=3 acts=[5, 15] new_line='    if x > t:'
   winner FIRST  order=[0, 10] repaired=True suite_runs=3 acts=[5, 15] new_line='    if x > t:'
   winner LAST   order=[10, 0] repaired=True suite_runs=3 acts=[5, 15] new_line='    if x > t:'
   reversed      order=[10, 0] repaired=True suite_runs=3 acts=[5, 15] new_line='    if x > t:'

================ fixture 'add': 'return a - b if a >= 0 else 1'
  kinds on the line: [(0,'strictness'),(1,'literal-off-by-one'),(2,'swapped-return-operands'),
                      (3,'flipped-additive'),(10,'flipped-comparison-direction'),
                      (11,'reversed-minus-operands')]
  --- A: no deadline ---
   loop order    order=[0, 1, 2, 3, 10, 11] repaired=True suite_runs=7 ...
   winner FIRST  order=[3, 0, 1, 2, 10, 11] repaired=True suite_runs=7 ...
   winner LAST   order=[0, 1, 2, 10, 11, 3] repaired=True suite_runs=7 ...
   reversed      order=[11, 10, 3, 2, 1, 0] repaired=True suite_runs=7 ...
```

`order_effect.py`'s deadline block (part B) appeared to show winner-first repairing and
winner-last refusing on the `cmp` fixture. That was wall-clock jitter, not an order effect -
repeating it five times per order shows both orders identical:

```
Part 2  deadline=0.95s (full search 2.11s), 5 repeats per order
   winner FIRST order=[3, 0, 1, 2, 10, 11]
      (repaired, suite_runs) x5 = [(False, 4), (False, 4), (False, 4), (False, 4), (False, 4)]
   winner LAST  order=[0, 1, 2, 10, 11, 3]
      (repaired, suite_runs) x5 = [(False, 4), (False, 4), (False, 4), (False, 4), (False, 4)]
```

### F3. Measured recurrence in the two histories, and what reordering by it would be worth

`scan_pairs.py` then `dedupe.py` over 4,000 commits per repo. Re-ran `dedupe.py` this session;
output is byte-identical to the stored `dedupe_output.txt` (`diff` -> IDENTICAL).

```
paired lines: 6463 -> unique (repo,old,new): 3920
box2d: ... comment/#include lines excluded: {'other-token': 825, 'other-literal': 4,
                                             'off-by-one': 3, 'compare': 2, 'sign': 2}
cglm:  ... comment/#include lines excluded: {'other-token': 491, 'sign': 10,
                                             'off-by-one': 8, 'other-literal': 6, 'compare': 3}
reachable unique pairs: 50 (Counter({'cglm': 44, 'box2d': 6}))
winning class, unique pairs: [(('cglm','literal-off-by-one'),40), (('box2d','flipped-additive'),3),
   (('box2d','strictness'),2), (('cglm','flipped-comparison-direction'),2),
   (('box2d','literal-off-by-one'),1), (('cglm','strictness'),1), (('cglm','flipped-additive'),1)]
```

Replaying the candidate stream on each defect line (position of the maintainer's exact fix - the
number that *would* be the saving if the loop stopped at the first green, which per F2 it does
not):

```
=== candidates tried on the defect line before the exact fix, unique reachable pairs ===
  loop (kind id, lanes.EMIT)       box2d= 12 cglm=142 total=154  (n=50)
  recurrence same repo, LOO        box2d= 12 cglm=151 total=163  (n=50)
  cheapest kind first              box2d= 12 cglm=138 total=150  (n=50)
  winner first (oracle bound)      box2d=  9 cglm=136 total=145  (n=50)
unique reachable pairs with >1 kind on the line (order can matter): 9 of 50
```

Two things follow. The whole spread between the shipped order and a perfect oracle is
154 -> 145, i.e. **9 candidate positions over 50 defects (5.8%)**. And ordering by measured
recurrence is **worse than the shipped order** (163 vs 154, +5.8%), because cglm's recurrence is
dominated by `literal-off-by-one`, which is kind id 1 and therefore already second in the
shipped ascending-id order; promoting it displaces `strictness` (kind 0) and pushes the
comparison-direction winners later. Only 9 of 50 defect lines carry more than one kind at all,
so on 41 of 50 there is no order to choose.

### F4. The coordinator's recurrence figures were not reproduced

TARGETS.md line 18 cites "Box2D: off-by-one 14, compare 4, logic 3, boundary 2, sign 2; cglm:
off-by-one 4, compare 2". I found no file in `research/laws-2026-09-07/` recording that scan's
method (`grep -rn "off-by-one" TARGETS.md FINDINGS.md QUEUE.md` matches only TARGETS.md itself),
so I could not replicate its labelling rule. My independent scan does not land on those numbers
under any of the three cuts I ran: raw paired lines give box2d off-by-one 22 / compare 2 / sign 6
(`pairs_output.txt`), unique pairs give box2d off-by-one 3 / compare 2 / sign 2 (above), and
whole-commit one-line fixes give box2d off-by-one 0 / cglm off-by-one 2 (`scan_output.txt`). My
labeller emits no "logic" or "boundary" counts for either repo. Whether the coordinator's figures
are reproducible is **unmeasured**; the numbers in F3 are the ones I stand behind, with the
script that produced them.

### F5. The ranking law has no lane that can see a class, and its byte is full

`nice -n 15 perl -e 'alarm 120; exec @ARGV' .venv/bin/python rank_side.py`:

```
rank.BITS = ['FRAME','FAILONLY','NAMED','SIGNALED','RECENT','CHEAP','DENSE','RETRIED']
            (8 lanes, byte is full)

[1] guard.py:409 packs the class as `signaled=bool(obs.kinds)`.
    byte= 13 (0b00001101) rank=0  <- kind sets [(1,),(10,),(0,),(3,),(0,10),(1,3,11),(0,1,2,3,8,9,10,11,12)]
    distinct bytes over those 7 kind sets: 1  ->  class identity is not representable
```

`SIGNALED` is a boolean on non-emptiness. Two candidate lines differing only in *which* class
matched pack to the same byte and necessarily receive the same priority. Every one of the eight
lanes is assigned, bit 7 being the RETRIED veto, and `rank()` is verified over exactly 256 inputs
(`cli.py:492-495`, `tests/test_rank_law.py`). A RECURRENT lane is therefore a **ninth** bit: a
re-authored kernel, not an edit.

### F6. Priority 1 is unreachable today because FAILONLY is never measured for lines

`rank_side.py`, same run:

```
[3] FAILONLY (bit 1) is never set by guard.rank_observations, so the
    body can construct 128 of 256 situations.
    rank distribution, all 256      : {0: 64, 1: 32, 2: 16, 3: 8, 4: 4, 5: 2, 6: 1, 7: 129}
    rank distribution, reachable 128: {0: 32, 2: 16, 3: 8, 4: 4, 5: 2, 6: 1, 7: 65}
    priorities unreachable with FAILONLY==0: [1]
```

`grep -rn "failonly" src/fluidfix/*.py` confirms the only `failonly=` assignment is
`guard.py:284`, which feeds the **SIGHT** law (file level), not `rank`. `rank_observations`
(lines 406-414) passes seven bits and omits `failonly` - documented at `guard.py:352-354`, not
forgotten.

### F7. The one channel through which class order still reaches a shipped law

`grep -rn "\.kinds" src/fluidfix/*.py` returns exactly three consumers:

```
guard.py:402:                    for k in (obs.kinds or [])[:2])     <- ORDER-SENSITIVE
guard.py:409:            signaled=bool(obs.kinds),                    <- order-insensitive
loop.py:283:            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)  <- ORDER DISCARDED
```

`guard.py:399-405` counts candidates for the first two kinds only and sets `CHEAP = 0 < n < 8`.
So kind order cannot touch the class search order, but it can flip CHEAP and thus the **line**
order. On real history lines (`cheap_channel.py`):

```
unique history lines carrying >=3 kinds (so the [:2] slice can differ): 231
  FLIPS  box2d  9f3c5c90d1 kinds=[0, 1, 10] | CHEAP=True at [:2]=[0, 10] n=4; CHEAP=False at [:2]=[0, 1] n=8
  FLIPS  box2d  d1581fb721 kinds=[1, 3, 11] | CHEAP=True at [:2]=[1, 11] n=7; CHEAP=False at [:2]=[1, 3] n=8
  FLIPS  box2d  d1581fb721 kinds=[1, 3, 11] | CHEAP=True at [:2]=[3, 11] n=6; CHEAP=False at [:2]=[1, 3] n=12
lines (of the 40 examined) where kind ORDER alone flips the CHEAP bit: 5
```

5 of the 40 examined lines (12.5%) change a ranking-law input bit on kind order alone.

### F8. Class recurrence is not among the git facts the body already reads

The body reads git in two places. `hotspots.bugfix_churn` returns "file -> bug-fix touches" - a
**file**-level counter, no class label anywhere in it. `guard._recent_lines` blames a file against
the last 40 commits to set RECENT - a **line**-level recency set. Neither yields per-class
recurrence; producing it requires labelling historical diffs by class, which is what
`scan_history.py` does here and which nothing in `src/` does.

## 4. Lanes

Ranking law lanes this work reached: **SIGNALED** (set on every observation the mechanical
observer produces), **CHEAP** (shown flip-able on kind order, F7), and the tie-break path under
the law at `guard.py:422-427`. Lanes reached only by enumeration, never by a real body run in
this work: FRAME, NAMED, RECENT, DENSE, RETRIED - **unmeasured** here (target 15 owns that audit).

Lanes never reached by the body at all: **FAILONLY** (bit 1). It is never assigned in
`rank_observations`; consequently **priority 1 is unreachable** and the body constructs 128 of
the law's 256 situations (F6). The observation that would make it reachable is line-level
coverage of the failing set and of the passing set separately - `coracle.py` already computes
file-level specificity from coverage (`coracle.py:311-320`, `guard.py:284`), so the missing piece
is per-line, per-test coverage rather than a new tool.

Lane the law does not have: a **RECURRENT** lane. There is no spare bit (F5).

Loop lanes: `lanes.EMIT/ADVANCE/HALT` were exercised over the full 9-kind mask; `HALT` and the
NOPROGRESS/dedupe skips were reached. The AMB early break (`loop.py:415`) and the `SpanEdit`
branch were **not** reached by these fixtures.

## 5. Potential

- **Perfect class ordering is worth 9 candidate positions on 50 real defects (5.8%)** - the
  measured gap between the shipped ascending-kind-id order (154) and an oracle that always tries
  the winning class first (145). Ordering by measured recurrence does not capture that gap; it
  loses 9 positions to the shipped order (163). Cheapest-kind-first is the only reordering that
  beat the shipped order, and only by 4 positions (150).
- **In the shipped loop that 5.8% is worth zero suite runs**, because the search is exhaustive
  over kinds (F2) and the order is not representable anyway (F1). It becomes worth something only
  in the budget-truncated regime, where `guard.py`'s `first_deadline`/`escalate_budget` cut the
  search short - how many real refusals that would convert to repairs is **unmeasured**.
- **The unbuilt FAILONLY measurement** would give the ranking law back its priority-1 lane and
  double its reachable situation space from 128 to 256 bytes. What that is worth in repairs or
  suite runs is **unmeasured**.
- Vocabulary coverage, not ordering, is where the mass sits: of 3,920 unique changed-line pairs
  in fix commits, **50 (1.3%)** are reachable by any shipped class at all (F3). The largest
  single unreachable group my labeller found is off-by-one fixes that **increment** (bug =
  correct - 1) - 21 in Box2D and 5 in cglm, listed in `offbyone_increments.txt` - for which no
  shipped applier generates the candidate (`literal-off-by-one`'s applier reduces).

## 6. Defects

**None found in any ruling.** One defect found, classified **observation**, plus one wording note.

- **Observation.** `acts.Observation` documents `kinds` as "most specific first" (`acts.py:60`),
  and taught/LLM observers are free to order that list; `loop.py:283` converts it to a bitmask and
  destroys the order (F1, Part 0: 720 permutations -> 1 mask). The observer's specificity ordering
  is measured and then thrown away. No wrong repair is attributable to it here - F2 shows the
  completed-search cost is order-invariant, so today the loss is silent rather than harmful. It
  becomes a real loss the moment a wall-clock deadline truncates the search, which is the exact
  regime `rank.py`'s own docstring was authored for (click, 2026-09-02, 1,934s / 474 candidates).
  The fix is an observation-plumbing one - carry the order, e.g. iterate the deduplicated
  `obs.kinds` directly instead of an unordered mask - not a new `if`.
- **Wording (minor).** `guard.py:402` slices `(obs.kinds or [])[:2]` to measure CHEAP. The
  docstring at `guard.py:351` lists CHEAP as one of the bits "measured here" without recording
  that it is measured on an arbitrary two-kind prefix of a list whose order the rest of the body
  discards. On 5 of 40 real history lines that prefix alone decides the bit (F7).
- **Not a defect: the recurrence ordering itself.** The law was never asked. Class order is not a
  ruling of `rank.py`, which ranks lines; it is `lanes.EMIT` over `acts.KINDS` ids. Nothing ruled
  wrong because nothing ruled.

## 7. Verdict

Ordering fault classes by measured recurrence would save **zero** suite runs in fluidfix as
shipped - the loop is exhaustive over kinds and `loop.py:283`'s bitmask makes class order
unrepresentable - and on the 50 reachable Box2D/cglm defects recurrence order is measurably
*worse* than the shipped order (163 vs 154 candidate positions, against an oracle bound of 145);
recurrence is not the ranking law's business, since `rank.py` ranks lines and its eight lanes are
all assigned, so it is a ninth bit the law lacks rather than one it mismeasures - while the lane
it does have and the body never sets, FAILONLY, already costs it priority 1 and half its
situation space.
