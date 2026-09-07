# 12-rank-winning-class

## 1. Target
On the Python fixtures in `tests/`, log the rank the ranking law (`src/fluidfix/rank.py`) gives each candidate class and which class actually repairs; report the distribution of "rank of the winner".

## 2. Method

Work in this directory was started by an earlier, interrupted run. I inspected it first, reproduced it, then extended it. Nothing in `src/`, `tests/` or `docs/` was touched.

Inherited and verified (written by the earlier run, kept as-is):
- `rank_winners.py` — the harness. Builds 35 throwaway projects under `runs/` from fixtures copied verbatim out of `tests/`, `docs/` and `examples/`, then runs `guard_once()` on each with three monkeypatches held only for the duration of that call: `fluidfix.rank.rank` (records the byte and priority of every observation the law ranks), `fluidfix.loop.candidates` (records every candidate set, its line, its kind and its contents in the exact order the body asked) and `Oracle.check` (records every real suite run together with the diff that was on disk at that moment). Writes `log/<name>.json`.
- `analyze.py` / `analyze.out` — aggregation of those logs.
- `dead_lanes.py` / `dead_lanes.out` — exhaustive check that RECENT/CHEAP/DENSE are inert once SIGNALED is set, plus the `retried=` call-site audit.
- `log/` — 34 fixture logs (27 repaired, 7 refused). `runs/` — the throwaway projects.

Completed and added by this run:
- `heavy_rank_only.py` -> `heavy_rank_only.out`. The earlier run left this output file empty (0 bytes). Re-run to completion here. It ranks the CAPPED-escalation fixture's packets without running any repair.
- `lane_reach.py` -> `lane_reach.out`. Exhaustive: all 256 law inputs, then the subset the body can actually construct.
- `class_order.py` -> `class_order.out`. Exact attribution of every pre-winner suite run to the LINE / CLASS / CANDIDATE dimension, by walking the candidate log in body order against the check log.
- `winner_rank.py` -> `winner_rank.out`. The headline distribution, plus per-priority precision.
- `repro.out` — reproduction check.

Read: `src/fluidfix/rank.py` (whole), `src/fluidfix/guard.py:340-428` (`rank_observations`), `src/fluidfix/loop.py:260-330`, `src/fluidfix/observers.py:28-44`, `src/fluidfix/lanes.py:20-32`, `tests/test_regressions.py:26-45`.

**Environment note.** `timeout(1)` is not installed on this machine (`which timeout` -> nothing, `gtimeout` -> not found). The brief's `timeout 300` was emulated as `nice -n 15 perl -e 'alarm 300; exec @ARGV' <cmd>`, one run at a time. Every command below is quoted in that form.

## 3. Findings

### F1. The ranking law ranks LINES. It has no input for a class, so "the rank of the winning class" is only definable as the rank of the line that class sits on.

`rank.py` docstring line 6: "Ranks ONE candidate line for repair." Its eight bits are all line-scoped. The body's measurement function is keyed on `obs.lineno`:

```
$ sed -n '396,414p' src/fluidfix/guard.py
    def priority(obs):
        ln = obs.lineno
        ...
            n = sum(len(candidates(body.strip(), act_for(k), obs))
                    for k in (obs.kinds or [])[:2])
            cheap = 0 < n < 8
        ...
        return _rank(observe_bits(
            frame=ln in framed,
            ...
            signaled=bool(obs.kinds),
```

Class order inside a line is decided elsewhere, by the LANES law iterating a bitmask of kind ids:

```
$ grep -n "mask = mask_of\|kind = kind_of(EMIT\|mask = ADVANCE" src/fluidfix/loop.py
283:            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
297:                kind = kind_of(EMIT(mask))
298:                mask = ADVANCE(mask)
$ grep -n "def EMIT" -A 2 src/fluidfix/lanes.py
20:def EMIT(m: int) -> int:
21-    return m & (-m)
```

`EMIT` is the lowest set bit, so classes are tried in **ascending kind id** — the number the dictionary registered the class under. That number is not evidence, and `rank.py` never sees it.

### F2. 80% of the suite runs wasted before a repair are spent in that unranked class dimension.

`class_order.py` attributes every recorded suite run before the first green to a `(line, kind)` slot by walking the candidate sets in the exact order the body asked for them and consuming candidates until one matches the text the check saw on disk (so candidates the body skips without a suite run — NOPROGRESS, out-of-bounds SpanEdit — are skipped by the same walk). Zero checks failed to match.

```
$ nice -n 15 .venv/bin/python class_order.py
TOTAL                                                       25    5   20    0     0   0
total suite runs over the 27 repaired fixtures (red precondition, every candidate, confirm): 108
WASTED runs (a candidate applied, suite red, before the winner): 25
  LINE dimension      (ranking law rules this)   5 = 20%
  CLASS dimension     (no law rules this)       20 = 80%
  CANDIDATE dimension (dictionary order)         0 = 0%
  unmatched checks (attribution failed): 0
```

This agrees exactly with the earlier run's independent, diff-based method (`analyze.out` line 51: "TOTAL wasted checks before winner: 25 = other line 5 + other kind on winner line 20 + earlier candidate of winning kind 0"). Two different methods, same split.

The winning class was **not** the first class tried on its own line in 13 of 27 fixtures:

```
winning class's position among the classes on its own line (body order):
  {'1/1': 11, '1/2': 3, '2/2': 3, '2/3': 5, '3/3': 1, '3/4': 3, '4/4': 1}
winner was the FIRST class tried on its line in 14/27 fixtures; NOT first in 13
```

The CANDIDATE column is 0: once the body reached the right `(line, class)` slot, the first candidate in the set was the repair every single time in this corpus.

### F3. Distribution of the rank of the winner.

```
$ nice -n 15 .venv/bin/python winner_rank.py
== distribution of the rank of the winner (27 repaired fixtures) ==
law priority of the winning line: {0: 12, 2: 1, 3: 14}
winner's position in the law's RANKED order: {1: 23, 2: 3, 3: 1}
winner's position in raw LINE order (what you get with no law): {1: 16, 2: 9, 3: 1, 4: 1}
winner's bits: {'SIGNALED+CHEAP': 11, 'FRAME+NAMED+SIGNALED+CHEAP': 8,
                'FRAME+SIGNALED+CHEAP': 4, 'SIGNALED': 3, 'NAMED+SIGNALED+CHEAP': 1}
```

The law put the winning line first in 23/27; raw line order would have put it first in 16/27. It moved the winner up in 7 fixtures, jumping 9 lines in total:

```
7/27 fixtures: [('ctx_zero_guard_r2', 4, 1), ('demo_invoices_dict', 2, 1),
 ('demo_metrics_dict', 2, 1), ('dict_payroll', 2, 1), ('guard_join2', 2, 1),
 ('proof_member4_cart', 2, 1), ('teach_get_default', 2, 1)]
lines the law jumped over, total: 9
```

### F4. Priority 0 was never wrong on this corpus; priority 3 is a coin flip.

Counted over the ranking table that governed the file the repair landed in, for each of the 27 repaired fixtures:

```
priority  observations  were the winner  precision
0         12            12               12/12 = 100%
2         3             1                1/3 = 33%
3         33            14               14/33 = 42%
```

Priority 0 requires FRAME (the failing traceback names that exact line). Every time the body could measure FRAME, the framed line was the defect.

### F5. Only 3 of the law's 8 priority classes are reachable by the body today.

```
$ nice -n 15 .venv/bin/python lane_reach.py
== all 256 inputs ==
priority histogram over all 256: {0: 64, 1: 32, 2: 16, 3: 8, 4: 4, 5: 2, 6: 1, 7: 129}

== the body's pinned lanes ==
SIGNALED: guard.py:409  signaled=bool(obs.kinds)  -> 1 whenever an observation exists
FAILONLY: never measured (guard.py:351-354 docstring)          -> always 0
RETRIED : neither rank_observations call site passes retried=   -> always 0

bytes the body can construct today: 32
their priority histogram: {0: 16, 2: 8, 3: 8}
distinct priorities reachable today: [0, 2, 3]

== which free lanes can move the priority at all, given SIGNALED=1 ==
  FRAME    : flipping it changes rank() on 32 of the 32 reachable bytes
  NAMED    : flipping it changes rank() on 16 of the 32 reachable bytes
  RECENT   : flipping it changes rank() on  0 of the 32 reachable bytes
  CHEAP    : flipping it changes rank() on  0 of the 32 reachable bytes
  DENSE    : flipping it changes rank() on  0 of the 32 reachable bytes
```

The RETRIED audit is the earlier run's, reproduced in `dead_lanes.out`:

```
rank_observations call sites in guard.py and whether `retried=` is passed:
  guard.py:511: retried passed = False
  guard.py:585: retried passed = False
```

So of eight lanes, **two** can discriminate today (FRAME, NAMED), one is a constant (SIGNALED, F6), three are masked by that constant (RECENT, CHEAP, DENSE), one is documented-unmeasured (FAILONLY) and one is never passed (RETRIED).

### F6. SIGNALED is not an observation on the mechanical path — it is definitionally 1.

```
$ sed -n '36,41p' src/fluidfix/observers.py
                kinds = [k for k, (_, _, sig) in sorted(KINDS.items())
                         if sig.search(line)]
                if kinds:
                    obs.append(Observation(lineno=l, kinds=kinds))
```

`MechanicalObserver` only constructs an `Observation` when `kinds` is non-empty, and `guard.py:409` measures `signaled=bool(obs.kinds)`. An unsignaled line is therefore never offered to the law. Measured, over every observation the body ranked in these runs:

```
$ nice -n 15 .venv/bin/python dead_lanes.py
observations: 57; SIGNALED set on 57; RECENT 0; CHEAP 54; DENSE 0; FAILONLY 0;
 RETRIED 0; FRAME 12; NAMED 12
```

57/57, and 802/802 on the heavy fixture (F8). The one path that can produce SIGNALED=0 is the LLM observer (`observers.py:161`, whose prompt at line 56 explicitly calls the empty kinds list "a correct and valued answer"); that path was not exercised here — unmeasured.

Note the same line also fixes the class order: `sorted(KINDS.items())` emits kinds ascending, which is exactly the order `EMIT` then consumes.

### F7. CHEAP is computed at real cost, samples only the first two classes, and has no effect on any reachable input.

```
$ sed -n '399,403p' src/fluidfix/guard.py
        try:                       # CHEAP: few candidates, no suite runs
            from .acts import act_for, candidates
            n = sum(len(candidates(body.strip(), act_for(k), obs))
                    for k in (obs.kinds or [])[:2])
            cheap = 0 < n < 8
```

`candidates()` is called for up to two kinds of every observation, so on a line with 3 or 4 classes the bit is measured from a partial sample. It was set on 54 of 57 observations — and per F5 it changes the output on 0 of the 32 bytes the body can construct.

### F8. On the CAPPED-escalation fixture the law returns one flat priority for all 802 observations; the defect sits at position 401 of 802.

```
$ nice -n 15 perl -e 'alarm 300; exec @ARGV' .venv/bin/python heavy_rank_only.py
defect line: 403  ('if v > limit:')
candidate files: ['mod.py']

max_lines=110: packet lines=110 truncated=True observations=110 kinds histogram={12: 109, 1: 1}
  priority histogram: {3: 110}
  defect line 403 in packet: NO (outside the spread sample) -> first pass cannot repair; CAPPED lane

max_lines=990: packet lines=803 truncated=False observations=802 kinds histogram={12: 800, 0: 1, 10: 1, 1: 1}
  priority histogram: {3: 802}
  defect line 403 in packet: yes; ranked position 401/802; priority 3 bits=SIGNALED+CHEAP;
   same-priority lines ahead: 400; candidate sets (one suite run each, all red) ahead of it: 400
```

Every observation lands in one class, so `guard.py:425-427`'s tie-break — `(priority, -shared name tokens, input index)` — falls through to input index, i.e. raw line order. The law contributes nothing here. Two of its own lanes would have discriminated (the 800 filler lines share a shape, so DENSE; the defect line does not) but both are masked by the constant SIGNALED.

### F9. The one fixture whose outcome differs from its source test is a harness expectation, not a fluidfix defect.

`analyze.out` line 3 flags `regress_crlf_cmp` as expected-repaired / actually-refused. The source test hands `repair()` a hand-written single observation:

```
$ sed -n '42,44p' tests/test_regressions.py
    result = repair(oracle, "mod.py", [Observation(lineno=2, kinds=[0])])
    assert result.repaired
```

The harness instead ran the full `guard_once()` with `MechanicalObserver`, which found two lines carrying three classes between them, and the engine law ruled AMB:

```
$ .venv/bin/python -c "import json; r=json.load(open('log/regress_crlf_cmp.json')); print(r['hint'])"
AMBIGUOUS: 2 candidates at 2 different lines (2, 3) all pass the suite — the tests cannot
tell them apart, and one may CANCEL the fault rather than repair it. Add one pinning test
```

Both greens are real (`if x > t:` from kind 0 and `return 0` from kind 1 both satisfy `cmp(5,5) == 0`). The ruling is correct; `expect="repaired"` in `rank_winners.py:217` was the wrong expectation to record. Left in place and corrected here rather than edited, so the earlier run's output stays reproducible.

### F10. The logs reproduce byte-for-byte.

```
$ nice -n 15 perl -e 'alarm 300; exec @ARGV' .venv/bin/python rank_winners.py \
    --only proof_member2_metrics,demo_billing,e2e_count_above,teach_get_default,span_guarded,regress_crlf_cmp
e2e_count_above    repaired 6.0s runs=6  win L4 kind=0(strictness) prio=3 bits=SIGNALED+CHEAP pos=2/3 ...
$ # diff each re-run log against a backup of the original, ignoring wall-clock seconds
proof_member2_metrics    IDENTICAL
demo_billing             IDENTICAL
e2e_count_above          IDENTICAL
teach_get_default        IDENTICAL
span_guarded             IDENTICAL
regress_crlf_cmp         IDENTICAL
```

## 4. Lanes

Ranking law lanes and priority classes this work reached:

| lane | reached | evidence |
|---|---|---|
| FRAME | yes, 12/57 observations | `dead_lanes.out`; every one of them was the winner (F4) |
| NAMED | yes, 12/57 | `dead_lanes.out` |
| SIGNALED | yes, 57/57 — but as a constant, never as a discriminator (F6) | `observers.py:39` |
| CHEAP | measured 54/57, inert on all 32 reachable bytes (F7) | `lane_reach.out` |
| RECENT | never set: 0/57. The fixtures are bare directories, and the brief forbids state-changing git, so `_recent_lines` finds no repository. It is not broken — `dead_lanes.out` shows it returning 95 lines when pointed at the fluidfix repo itself | `dead_lanes.out` |
| DENSE | never set in the 57 fixture observations. On the heavy fixture the 800 filler lines share a shape and should set it, but their bytes were not recorded — **unmeasured** | `dead_lanes.out` |
| FAILONLY | never reached. `guard.py:351-354` documents it as unmeasured; needs line-level coverage of the passing tests as well as the failing ones | `lane_reach.out` |
| RETRIED (the veto) | never reached. Neither call site passes `retried=` | `dead_lanes.out` |

Priority classes: **0, 2 and 3 reached** (12, 3 and 33 observations across the governing tables). **1, 4, 5, 6 and 7 never reached, and cannot be** with today's measurements — 1 needs FAILONLY, 4/5/6 need SIGNALED to be able to read 0, and 7 needs either an unsignaled line or the RETRIED veto.

The class dimension has no lane at all: `rank.py` takes no class-scoped input, and `loop.py:297` orders classes by kind id.

## 5. Potential

- **Ranking the class dimension.** 20 of the 25 wasted suite runs in this corpus (80%, F2) are spent on the wrong class of the right line. A per-`(line, class)` ranking call would be the actuation. Measured lower bound on what one cheap tie-break is worth: ordering the classes on a line by candidate-set size would have removed **4 of those 20** runs (`class_order.out`). That is a lower bound only — the sizes of class sets the body never reached were never computed, so whether a cheaper losing class would jump ahead of the winner is **unmeasured**.
- **Measuring FAILONLY.** It would change the priority of **16 of the 32** bytes the body can construct (`lane_reach.out`), splitting today's 33-observation priority-3 bucket — the bucket whose precision is 42%. What that is worth in saved suite runs is **unmeasured**: it needs line-level coverage of the passing tests, which `coracle.py` does not collect today.
- **Letting SIGNALED read 0.** Today it is a constant (F6), and it masks RECENT, CHEAP and DENSE — three lanes the law already has and the body already measures. On the heavy fixture that mask is worth up to **400 red suite runs** on a single defect (F8), because the 800 filler lines that DENSE would demote are ranked equal to the defect. Unmasking requires the body to offer unsignaled lines to the law (the LLM observer path can already produce them; the mechanical path cannot).
- **The RETRIED veto.** Never exercised, so its cost today is zero and its value is zero. It becomes reachable the moment `guard.py:511`/`585` pass the set of lines already rejected this pass — the escalation call at 585 re-ranks the same file after the first pass has rejected candidates on it, so the data exists at that call site. Value: **unmeasured**.
- **The CANDIDATE dimension needs nothing.** 0 of 25 wasted runs were spent on an earlier candidate of the winning class. No evidence here that candidate order inside a set is worth ranking.

## 6. Defects

**No wrong ruling found.** Every priority the body acted on matches `rank.py`'s formula — the harness records the law's own return value, and `lane_reach.py` re-derives all 256 independently. Where an outcome looked wrong, it was elsewhere:

1. **Observation.** SIGNALED is measured as `bool(obs.kinds)` (`guard.py:409`) but `MechanicalObserver` (`observers.py:39`) only builds an Observation when `kinds` is non-empty. The bit is a constant on that path, and because the law's lanes are strictly ordered it masks RECENT, CHEAP and DENSE entirely (0/32 reachable bytes, `lane_reach.out`). The law is ruling correctly on a situation the body cannot vary.
2. **Observation.** CHEAP samples only `obs.kinds[:2]` (`guard.py:402`), so on a 3- or 4-class line it is measured from part of the evidence. Harmless today only because CHEAP is masked by defect 1 — which is what makes it worth recording now.
3. **Actuation.** Class order within a line is chosen by `EMIT` over kind ids (`loop.py:297`), i.e. dictionary registration order. No law authored that order, and it is where 80% of the wasted suite runs go (F2). The gap is a missing actuation — a ranking call whose input is scoped to a `(line, class)` slot — not a missing `if`.
4. **Not a fluidfix defect.** `regress_crlf_cmp`'s repaired/refused mismatch is an incorrect `expect=` in this directory's own harness (F9). The engine law's AMB ruling on that observation byte is right.

## 7. Verdict
The ranking law ranks lines only and does that well on this corpus — winner first in 23/27 fixtures, priority 0 correct 12/12 — but the body pins SIGNALED to a constant that masks three of its lanes down to two live ones, and 20 of the 25 suite runs wasted before a repair are spent choosing among the classes on the already-correct line, a dimension no law rules today.
