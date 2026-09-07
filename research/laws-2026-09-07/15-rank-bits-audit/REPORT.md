# 15-rank-bits-audit

## 1. Target

For each of the ranking law's eight bits (`src/fluidfix/rank.py`), find the exact body
code that measures it and classify it **measured / approximated / hardcoded**.

## 2. Method

Read, in full: `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/rank.py`,
`guard.py` (lines 305-428 and the two call sites at 511 and 585), `observers.py`,
`localize.py:88-181`, `loop.py:163-419`, `coracle.py:670-771`, `javaoracle.py`,
`cli.py:479-500`.

Built on the earlier attempt already in this directory
(`reachable.py`/`reachable.out`, `bit_thresholds.py`/`.out`, `log_rank_bits.py` +
`rank_bits_summary.txt`, `frame_probe.py`/`.out`) and confirmed its central claim —
`guard.py` is the only body caller — then extended it in four directions with new
scripts, all in this directory:

| script | what it does | output |
|---|---|---|
| `bits_audit.py` | call-site census; drives the body's own `rank_observations` on a Python fixture and a C fixture; probes the `retried=` kwarg | `bits_audit.out` |
| `retried_cost.py` | real `guard_once` run on a fixture that takes **both** passes over one file; counts duplicated candidates | `retried_cost.out`, `retried_cost.json` |
| `retried_value.py` | fixture where the escalation packet contains lines pass 0 never saw; measures what the dead RETRIED veto would reorder | `retried_value.out` |
| `inert_bits.py` | exhaustive proof that RECENT/CHEAP/DENSE cannot decide on the mechanical path, plus the cost of computing CHEAP | `inert_bits.out` |

GNU `timeout` is not installed on this machine (`which timeout` -> not found;
`gtimeout` -> not found), so the brief's `nice -n 15 timeout 300` is provided by
`./run.sh`, which uses `nice -n 15` plus perl's `alarm 300`. Every run below went
through it. No `src/`, `tests/` or `docs/` file was touched; no git state changed.
Fixtures were created fresh inside this directory.

## 3. Findings

### F1. The bit-by-bit audit table

Every citation is a line in `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py`.

| # | bit | measuring code | classification |
|---|---|---|---|
| 0 | FRAME | 361-366 (regex at 364) | **measured**, Python-only (see F2) |
| 1 | FAILONLY | *none* | **hardcoded 0** — the name never appears in the `observe_bits(...)` call at 406-414; `rank.observe_bits`'s default supplies `False` |
| 2 | NAMED | 368-385 (regex 370, `ast.parse` 375) | **measured**, Python + pytest-only (see F2) |
| 3 | SIGNALED | 409, `signaled=bool(obs.kinds)` | **measured but degenerate**: constant 1 on the zero-token path (see F3) |
| 4 | RECENT | `_recent_lines` 310-331, used at 393 | **measured** (git blame); `depth: int = 40` at 310 is a hardcoded constant; inert (F4) |
| 5 | CHEAP | 399-405 | **approximated**: only `(obs.kinds or [])[:2]` are counted (402) and the threshold `0 < n < 8` (403) is hardcoded; a bare `except Exception: cheap = False` (404-405); inert (F4) |
| 6 | DENSE | `_shape` 334-337, counted 387-391, tested at 412 | **measured**; the threshold `>= 8` at 412 is hardcoded; inert (F4) |
| 7 | RETRIED | 394 (`retried = retried or set()`), 413 | **hardcoded 0** — the parameter exists, no call site passes it (F5) |

Command and excerpt (`bits_audit.py`, section D):

```
$ ./run.sh /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python bits_audit.py
  guard.py:511 call site kwargs -> NO retried kwarg
  guard.py:585 call site kwargs -> NO retried kwarg
```

The law itself is not in question. `fluidfix selfcheck` re-derives it:

```
$ ./run.sh ./.venv/bin/fluidfix selfcheck
ranking law vs specification, all 256:       256/256
ranking law veto dominance / monotonicity:   both hold
```

### F2. FRAME and NAMED are structurally unmeasurable outside Python

`guard.py:364` is `r"([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)"`. The literal
`.py` means no C, C++, or Java failing output can ever set FRAME. NAMED needs both
`ast.parse(src)` (375) and pytest's `^FAILED <path>::<name>` shape (370).

`bits_audit.py` section C runs the body's own `rank_observations` on C source with
one of the two real C failure shapes quoted in `coracle.py`'s own header comment
(lines 59-60), then repeats it with the output rewritten to name a `.py` file:

```
-- C source, real C failing-output shape
   rel='math_functions.c'  order in=[3, 8] out=[3, 8]
   line    3  byte 0x28 = SIGNALED+CHEAP                           rank=3
   line    8  byte 0x28 = SIGNALED+CHEAP                           rank=3

-- CONTROL: same C source, output rewritten to name a .py file
   rel='math_functions.py'  order in=[3, 8] out=[3, 8]
   line    3  byte 0x29 = FRAME+SIGNALED+CHEAP                     rank=0
   line    8  byte 0x28 = SIGNALED+CHEAP                           rank=3

   matches in the real C failing output: []
     SyntaxError: invalid syntax (<unknown>, line 1) -> line_toks stays empty, NAMED=0
   tokens from the C output: []
```

The defect line is rank-3 in C and rank-0 in the control — same source, same
evidence, only the file suffix differs.

This is moot in production today, because of F6.

### F3. SIGNALED is a constant on the zero-token path

`observers.py:36-41` appends an `Observation` only when `kinds` is non-empty, so
`bool(obs.kinds)` at `guard.py:409` is always `True` for every observation the
`MechanicalObserver` produces. Confirmed by the earlier attempt's in-process log of
real guard runs (`rank_bits_summary.txt`): SIGNALED set on 17 of 21 bytes, and the
four unset ones were direct `rank()` calls from `tests/test_rank_law.py`, not bytes
the body built (`log_rank_bits.py` tags body bytes with `_in_body`).

### F4. Five of the eight bits cannot change a ruling on the zero-token path

`rank()` returns the index of the lowest set evidence bit. With SIGNALED (bit 3)
pinned to 1 and FAILONLY (1) and RETRIED (7) pinned to 0, bits 4, 5 and 6 sit above
the deciding bit and are unreachable as rulings. Exhaustively (`inert_bits.py`):

```
   bytes checked: 32   (byte, bit) pairs where flipping RECENT/CHEAP/DENSE changes rank(): 0
   -> NONE. all three are inert on this path.
```

Together with the two hardcoded-zero bits, **five of eight bits are inert**. The
effective law on the mechanical path is three-valued — FRAME -> 0, else NAMED -> 2,
else 3 — which the earlier attempt verified exhaustively over all 32 constructible
bytes (`reachable.out`: `verified exhaustively over the constructible bytes: True`).

RECENT is not inert for lack of signal. Measured on the shared clones with the
body's own `_recent_lines` (`bit_thresholds.out`): `box2d src/contact_solver.c
recent 1103/2500 = 44.1%`, `cglm include/cglm/vec3.h recent 13/1278 = 1.0%`. The
signal is there; the lane below it always fires first.

Computing the inert CHEAP bit is cheap in absolute terms and should not be
overstated (`inert_bits.py`):

```
   110 observations, kinds=[1,3]
   rank_observations WITH CHEAP measured : 3.0 ms
   same call with candidates() raising   : 1.7 ms
   share of the ranking call spent on a bit that cannot decide: 42%
```

1.3 ms per file is negligible next to one suite run. The classification issue is the
bare `except Exception` at 404-405: a real failure inside `candidates()` is recorded
as "this line is not cheap", indistinguishable from a measurement.

### F5. The RETRIED veto is dead, and a second pass over the same file really happens

The data the veto needs already exists in the body. `loop.py:331` writes
`at_str = f"{defect_file}:{obs.lineno}"` into `res.tried_log` (347, 408), and
`guard_once` accumulates those into `attempts` (guard.py:518, 598). Neither
`rank_observations` call site converts it into the `retried` set.

A second pass over the *same* file is routine: `guard.py:509-510` adds a file to
`full_sight` only when its packet was **untruncated**, and `guard.py:574` skips only
files in `full_sight`. A truncated pass-0 file is therefore re-ranked at 585 with
`retried=None`. `loop.repair`'s own dedupe set is per-call (`loop.py:185`), so the
escalation pass re-runs the suite on candidates pass 0 already rejected.

`retried_cost.py` builds a fixture that takes exactly that route (88-line `mod.py`,
one failing test, `guard_once(files=["mod.py"], escalate=True, budget=240)`):

```
== status=refused  seconds=11.6
rank_observations calls (the body's ONLY ranking path): 2
  call 0: rel='mod.py'  n_obs=110  retried kwarg = None    suite_runs = 19
  call 1: rel='mod.py'  n_obs=6    retried kwarg = None    suite_runs = 19

OVERLAP between pass 0 and the escalation pass over the SAME file:
  pass 0 rejected      : 18 distinct candidates
  escalation rejected  : 18 distinct candidates
  IDENTICAL (file:line, candidate text) in both: 18
  -> 18/18 = 100% of the escalation pass's rejected candidates were already
     rejected in pass 0
```

**Stated precisely, and not more:** RETRIED is a *ranking* veto, not a skip. In this
first fixture the escalation packet contained no new lines, so the veto would have
reordered the 19 runs, not removed them. The 100% duplication is a separate
actuation gap (no cross-pass dedupe at all), reported as D2 below.

`retried_value.py` builds the case where the veto does buy something. Its fixture
exploits `localize.py:165`: the anchor filter keeps only lines matching
`[<>]=?|\d|\s[-+*/]\s|and|or|True|False`, so `total = max(total, total)` is dropped
from the truncated pass-0 packet, while `acts.KINDS[8]` (`\b(?:min|max)\(`) flags it
in the full-sight escalation packet.

```
  call 0: retried kwarg=None  distinct observed lines=[13, 28, 43]              suite_runs=7
  call 1: retried kwarg=None  distinct observed lines=[13, 28, 43, 63, 73, 83]  suite_runs=10

pass 0 actually TRIED lines : [13, 28, 43]
  of those, FRESH (never tried): [63, 73, 83]

TODAY the escalation order is:  [13, 28, 43, 63, 73, 83]
  first FRESH line sits at position 3 of 6
WITH retried=<pass 0's own tried_log lines> passed to the SAME function:
  [63, 73, 83, 13, 28, 43]
  first FRESH line sits at position 0 of 6

MEASURED: the escalation pass paid 6 suite runs on already-rejected lines
          before its first candidate on a FRESH line (total escalation suite_runs=10).
```

Six of the escalation pass's ten suite runs were spent on already-rejected lines
before the first fresh line was touched. Passing the set the body already holds
moves them last. No `src/` change was needed to show it: `retried_value.py` calls the
same unmodified `guard.rank_observations` with `retried=` filled in.

### F6. The ranking law is never consulted on the C or Java path

Call-site census (`bits_audit.py`, section A):

```
  src/fluidfix/guard.py:511: observations = rank_observations("\n".join(packet.src_lines),
  src/fluidfix/guard.py:585: observations = rank_observations("\n".join(packet.src_lines),
  src/fluidfix/coracle.py:758: observations = observer.observe([packet])[0]
  src/fluidfix/javaoracle.py:211: observations = observer.observe([packet])[0]
```

`cguard_once` and `jguard_once` hand the observer's output straight to `repair()`
unranked. Box2D and cglm — the repos this project's real measurements come from —
run through `cguard_once`. So the ranking law orders lines on the Python path only.

### F7. On the Claude-observer path the ranking law has nothing to order

`ClaudeObserver.observe` appends exactly one `Observation` per packet
(`observers.py:156-166`, `out.append([Observation(...)])`), and both call sites pass
a single packet (`observer.observe([packet])[0]`). So `rank_observations` receives a
one-element list and sorting it is a no-op. The earlier attempt's `reachable.out`
found priorities 4-7 reachable "on the claude observer path"; that is true of the
byte arithmetic but cannot change an order, because there is never more than one
candidate line to order.

## 4. Lanes

**Reached by this work.** Priorities 0, 2 and 3, on real `guard_once` runs and on the
direct probes: p=0 via FRAME (`bits_audit.out`, byte `0x2d`), p=2 via NAMED alone,
p=3 via SIGNALED alone (`0x28`, the overwhelmingly common byte in both fixtures).
Priority 7 reached only by supplying `retried=` from outside the body
(`retried_value.py`), which is not something the body does today.

**Never reached, and why.**

- **p=1 (FAILONLY)** — unreachable on every path, on every observer. FAILONLY is
  never passed to `observe_bits` at all. Making it reachable needs line-level
  coverage of the failing set *and* of the passing set; `guard.py:352-354` says so in
  the docstring, and `coracle.py`'s `_Coverage` already computes the failing-set half
  for C. The passing-set half, and a Python equivalent, are what is missing.
- **p=4, 5, 6 (RECENT, CHEAP, DENSE)** — computed on every candidate line and never
  able to decide, because SIGNALED below them is a constant (F3, F4). Reachable only
  for an observation with `kinds=[]`, which the Claude observer can produce but which
  yields no candidates to try, and which on the Claude path is the only observation
  anyway (F7).
- **p=7 (the RETRIED veto)** — the law's stated reason for existing
  (`rank.py:23-25`). Reachable the moment either call site passes
  `retried={lineno for at in attempts}`.

The whole law is unreached on the C and Java paths (F6).

## 5. Potential

- **RETRIED, wired at `guard.py:585`.** Measured on `retried_value.py`'s fixture: 6
  of the escalation pass's 10 suite runs were spent on already-rejected lines before
  the first fresh line. Wiring the veto moves them last. On real repos: **unmeasured**
  — this run used a synthetic fixture, not Box2D or cglm, and the C path does not
  call the law at all (F6).
- **The ranking law on the C path (F6).** Box2D's `contact_solver.c` packets are
  hundreds of lines; ordering them is exactly the gap `rank.py:27-32` was authored to
  close. Value: **unmeasured** here. The blocker is not the law but F2 — FRAME's
  regex and NAMED's `ast.parse` are Python-shaped, so wiring `rank_observations` into
  `cguard_once` unchanged would rank every C line SIGNALED-only (all p=3, no
  reordering). Two observations would make it real: a FRAME matcher for the C failure
  shapes `coracle.py:59-60` already parses, and a NAMED source other than `ast`.
- **FAILONLY (p=1).** The one lane no observer can reach. `coracle.py` already
  measures the failing-test executed set per file (`cov.lines(probe)`); the missing
  half is the passing-suite line set. Value: **unmeasured**.
- **The three inert bits.** Their measurement cost is 1.3 ms per ranking call
  (F4) — negligible. The cost of leaving them inert is not the CPU, it is that a
  reader of `rank_bits_summary.txt` sees CHEAP set on 16 of 21 bytes and reasonably
  concludes the bit is doing work. It is not.

## 6. Defects

**D1 — observation. FRAME and NAMED cannot be measured for non-Python sources.**
`guard.py:364` hard-requires a `.py` suffix; `guard.py:375` requires `ast.parse` to
succeed. Evidence: F2, with a same-source control that flips the defect line from
rank 3 to rank 0 on the file suffix alone. Not a wrong ruling — the law correctly
ranked the byte it was handed; the byte was missing two bits that the C failure
output actually contains.

**D2 — actuation. The escalation pass re-tries what pass 0 already rejected.**
`loop.py:185` scopes the dedupe set to one `repair()` call, and `guard.py:585` does
not pass `retried=`. Evidence: F5, `18/18 = 100%` identical rejected candidates
across the two passes, 19 suite runs each. Two separate missing actuations: the
ranking veto (`retried=`) and a cross-pass candidate memo. The engine law already
names the second one — `REFUTED -> HARVEST_COUNTEREXAMPLE`, which the fixture's own
refusal hint quotes — and the rejected candidates are already in `attempts`; nothing
consumes them.

**D3 — actuation. `cguard_once` and `jguard_once` never consult the ranking law.**
Evidence: F6, call-site census. `coracle.py:758` and `javaoracle.py:211` pass the
observer's output straight to `repair()`.

**D4 — wording. The docstring's account of which bits are live is incomplete.**
`guard.py:351-354` names FAILONLY as the one unmeasured bit ("documented, not
forgotten"). RETRIED is equally unmeasured — the parameter exists but no call site
fills it — and RECENT, CHEAP and DENSE are measured but cannot reach a ruling. A
reader of that docstring would conclude seven of eight bits are live; three decide.

**No ruling defect found.** `fluidfix selfcheck` re-derives all 256 rulings against
the specification, and veto dominance and monotonicity both hold. Every wrong or
wasteful outcome above lives in a bit that was not measured or an actuation that was
not wired.

**Also observed, outside this target's scope but adjacent to it.** When
`localize.build_packet` sets `truncated` via the *filter* branch
(`localize.py:171`) while `len(lo) <= max_lines`, the spread-sample at
`localize.py:178-179` has `stride < 1` and **upsamples**: `retried_cost.out` records
`n_obs=110` from six distinct line numbers, each repeated ~18 times. `repair()`'s
`tried` set absorbs the duplicates so no extra suite runs are paid, but
`rank_observations` scores every duplicate. Belongs to the SIGHT/localize agents
(16-20); noted here because it is what inflates the ranking law's input.

## 7. Verdict

Three of the ranking law's eight bits can decide anything on the only path that
consults it: FRAME and NAMED are measured but Python-only, SIGNALED is a constant,
FAILONLY and RETRIED are hardcoded zero, and RECENT/CHEAP/DENSE are measured but sit
above a bit that always fires first — the law is exact (256/256 by selfcheck), and
every gap found is a missing observation or a missing actuation.
