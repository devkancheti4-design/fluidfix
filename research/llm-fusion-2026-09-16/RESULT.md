# Can fluidfix find and fix a bug quickly in hundreds of files, and what does escalating to a model cost? (measured 2026-09-16)

Asked as a CTO would: on real repositories, with the repository's own suite as the only judge, how often does the
zero-token guard restore the exact line, how long does it take, how often is it wrong, what does it refuse, and
when it refuses, what does it cost in tokens to let a model author a rule that the same suite then judges.
Every number below is written by the harness that measured it (`scale_results.json`, `bench_real_results.json`,
`cases/*/*/rerun_budget*.json`, `ladder_*.json`); `report.py` renders the tables. Nothing is typed in by hand.

## 1. Protocol (fixed before the run)

- Repositories: click, arrow, sortedcontainers, rich. Shallow clones, own venv each, suite green at baseline
  (rich: 8 environment-dependent tests deselected in its pyproject, committed on the clone).
- Seed 20260916. Mutation sites found by regex over library files only, shuffled once with the seed, taken in
  order; no human choice. Liveness checked twice (red, restore green, red); dead and flaky mutants recorded.
- Classes. In vocabulary (tier 0 should repair): comparison strictness, additive +/- flip, numeric literal +1.
  Out of vocabulary (tier 0 must refuse; the ladder then runs): and/or flip, `.get(k, d)` -> `.get(k)`,
  `if not X` -> `if X`, `range(1, n)` -> `range(n)`, `len(x) - 1` -> `len(x)`. Two live mutants per in-vocab
  class, one per out-of-vocab class, at most 25 attempts per class.
- Tier 0: `fluidfix guard . --commit --budget 300`; verdict EXACT (pristine bytes back), WRONG-GREEN (suite passes,
  bytes differ), REFUSED, NO-ACTION. Refused cases are saved with the guard's refusal report.
- Ladder: each saved out-of-vocab refusal is replayed from the recorded refusal through `fuse.py` with one author
  at a time. Tier 1: the author writes a rule (signal + applier) from a compact packet; it is validated offline
  and installed in a throwaway dictionary; the guard re-runs with the same 300 s budget. Tier 2: the author
  proposes up to three direct replacements, wrapped as a one-line rule; same guard, same judge. The author never
  judges. Tokens are the runtime's own counts (Ollama `prompt_eval_count`/`eval_count`); my own authoring is
  counted as characters/4 and marked approximate.
- Hardware: one 12-core Mac. The click trials ran with at most one other job on the machine. The arrow trials
  ran while several of my follow-up jobs competed for CPU (load average 10.5); every arrow case is therefore
  replayed alone in the clean pass below, and the clean numbers are the ones to quote.

## 2. Hundreds of files: does it find the one that broke?

Synthetic package: 302 source files, 300 tests, green suite 3.5 s, seed 20260916. True file ranked first in 10/10 cases; byte-exact repair in 10/10; localisation 4.7–9.6 s; repair wall-clock median 16.0 s (min 14.5, max 17.4).

| file | injected fault (shipped kind) | rank of true file | localise s | suite runs | wall s | byte-exact |
|---|---|---|---|---|---|---|
| pkg/mod_021.py | 3 flipped-additive | 1 | 9.6 | 4 | 14.6 | yes |
| pkg/mod_195.py | 0 strictness | 1 | 4.7 | 8 | 15.9 | yes |
| pkg/mod_081.py | 8 minmax-swap | 1 | 4.9 | 9 | 15.7 | yes |
| pkg/mod_055.py | 1 literal-off-by-one | 1 | 4.8 | 10 | 16.0 | yes |
| pkg/mod_189.py | 9 flipped-augmented-assign | 1 | 4.8 | 12 | 16.8 | yes |
| pkg/mod_258.py | 10 flipped-comparison-direction | 1 | 4.9 | 14 | 17.4 | yes |
| pkg/mod_123.py | 3 flipped-additive | 1 | 4.7 | 4 | 14.5 | yes |
| pkg/mod_224.py | 0 strictness | 1 | 4.7 | 8 | 16.2 | yes |
| pkg/mod_293.py | 8 minmax-swap | 1 | 4.9 | 9 | 15.8 | yes |
| pkg/mod_256.py | 1 literal-off-by-one | 1 | 4.8 | 10 | 16.0 | yes |

## 3. Real repositories, tier 0 (zero tokens)

|  | live trials | byte-exact | wrong-green | refused | no-action |
|---|---|---|---|---|---|
| in-vocabulary | 22 | 7 | 1 | 14 | 0 |
| out-of-vocabulary | 16 | 0 | 0 | 16 | 0 |

In-vocabulary byte-exact repairs: median 83 s, min 46.6, max 217.1 s.

### click

Scans: cmp 2 live of 3 tried, add 2 live of 4 tried, lit 2 live of 2 tried, andor 1 live of 1 tried, getdef 1 live of 1 tried, notdrop 1 live of 1 tried, rangestart 0 live of 0 tried, lenm1 1 live of 1 tried.

| case | vocab | site | mutation | verdict | seconds | suite runs |
|---|---|---|---|---|---|---|
| cmp-1 | in | `src/click/_textwrap.py:111` | `if cur_len + n <= width:` → `if cur_len + n < width:` | REFUSED | 329.6 | - |
| cmp-2 | in | `src/click/_termui_impl.py:298` | `if self.length is not None and self.pos >= self.` → `if self.length is not None and self.pos > self.l` | EXACT | 86.2 | 36 |
| add-1 | in | `src/click/formatting.py:28` | `yield row + ("",) * (col_count - len(row))` → `yield row + ("",) * (col_count + len(row))` | EXACT | 217.1 | 48 |
| add-2 | in | `src/click/formatting.py:95` | `indent = orig_len - term_len(line)` → `indent = orig_len + term_len(line)` | EXACT | 83.3 | 55 |
| lit-1 | in | `src/click/_termui_impl.py:192` | `return f"{hours:02}:{minutes:02}:{seconds:02}"` → `return f"{hours:3}:{minutes:02}:{seconds:02}"` | REFUSED | 305.3 | - |
| lit-2 | in | `src/click/shell_completion.py:494` | `incomplete = split_arg_string(incomplete)[0]` → `incomplete = split_arg_string(incomplete)[1]` | EXACT | 65.5 | 16 |
| andor-1 | OOV | `src/click/shell_completion.py:467` | `help_ = item.help or "_"` → `help_ = item.help and "_"` | REFUSED | 302.1 | - |
| getdef-1 | OOV | `src/click/_termui_impl.py:579` | `less_env = os.environ.get("LESS", "")` → `less_env = os.environ.get("LESS")` | REFUSED | 49.9 | - |
| notdrop-1 | OOV | `src/click/shell_completion.py:664` | `if not value:` → `if value:` | REFUSED | 44.2 | - |
| lenm1-1 | OOV | `src/click/utils.py:84` | `last_index = len(words) - 1` → `last_index = len(words)` | REFUSED | 304.4 | - |

### arrow

Scans: cmp 2 live of 3 tried, add 2 live of 2 tried, lit 2 live of 5 tried, andor 1 live of 8 tried, getdef 1 live of 2 tried, notdrop 1 live of 1 tried, rangestart 0 live of 0 tried, lenm1 1 live of 1 tried.

| case | vocab | site | mutation | verdict | seconds | suite runs |
|---|---|---|---|---|---|---|
| cmp-1 | in | `arrow/locales.py:1340` | `elif 2 <= delta % 10 <= 4 and (delta % 100 < 10 ` → `elif 2 < delta % 10 <= 4 and (delta % 100 < 10 o` | REFUSED | 303.3 | - |
| cmp-2 | in | `arrow/parser.py:786` | `if am_pm == "pm" and hour < 12:` → `if am_pm == "pm" and hour <= 12:` | REFUSED | 303.4 | - |
| add-1 | in | `arrow/arrow.py:1223` | `calendar_diff.years * self._MONTHS_PER_YEAR + ca` → `calendar_diff.years * self._MONTHS_PER_YEAR - ca` | WRONG-GREEN | 113.7 | 25 |
| add-2 | in | `arrow/arrow.py:574` | `for _ in range(3 - len(values)):` → `for _ in range(3 + len(values)):` | REFUSED | 302.5 | - |
| lit-1 | in | `arrow/locales.py:5495` | `"hours": {"double": "{0} sata", "higher": "{0} s` → `"hours": {"double": "{0} sata", "higher": "{1} s` | REFUSED | 244.5 | - |
| lit-2 | in | `arrow/locales.py:4601` | `"years": "{0} बर्ष",` → `"years": "{1} बर्ष",` | REFUSED | 224.9 | - |
| andor-1 | OOV | `arrow/locales.py:5468` | `if n > 10 or n == 0:` → `if n > 10 and n == 0:` | REFUSED | 308.2 | - |
| getdef-1 | OOV | `arrow/parser.py:797` | `if parts.get("microsecond", 0) != 0:` → `if parts.get("microsecond") != 0:` | REFUSED | 205.0 | - |
| notdrop-1 | OOV | `arrow/arrow.py:1418` | `if not match:` → `if match:` | REFUSED | 204.3 | - |
| lenm1-1 | OOV | `arrow/locales.py:3636` | `elif index == len(timeframes) - 1:  # Must have ` → `elif index == len(timeframes):  # Must have at l` | REFUSED | 302.0 | - |

### python-sortedcontainers

Scans: cmp 2 live of 7 tried, add 2 live of 2 tried, lit 2 live of 2 tried, andor 1 live of 10 tried, getdef 0 live of 0 tried, notdrop 1 live of 1 tried, rangestart 1 live of 1 tried, lenm1 1 live of 2 tried.

| case | vocab | site | mutation | verdict | seconds | suite runs |
|---|---|---|---|---|---|---|
| cmp-1 | in | `src/sortedcontainers/sortedlist.py:1325` | `if start < 0:` → `if start <= 0:` | EXACT | 75.8 | 78 |
| cmp-2 | in | `src/sortedcontainers/sortedlist.py:1535` | `assert self._lists[pos - 1][-1] <= self._lists[p` → `assert self._lists[pos - 1][-1] < self._lists[po` | REFUSED | 202.0 | - |
| add-1 | in | `src/sortedcontainers/sortedlist.py:955` | `next_pos = min_pos + 1` → `next_pos = min_pos - 1` | REFUSED | 256.2 | - |
| add-2 | in | `src/sortedcontainers/sortedlist.py:2508` | `elif child + 1 == len(self._index):` → `elif child - 1 == len(self._index):` | REFUSED | 203.5 | - |
| lit-1 | in | `src/sortedcontainers/sortedlist.py:2421` | `SortedKeyList([3, 3, 2, 2, 1, 1], key=<built-in ` → `SortedKeyList([3, 3, 2, 3, 1, 1], key=<built-in ` | EXACT | 151.2 | 56 |
| lit-2 | in | `src/sortedcontainers/sortedset.py:639` | `SortedSet([1, 2, 3, 4, 5, 6, 7])` → `SortedSet([1, 2, 3, 4, 5, 7, 7])` | EXACT | 46.6 | 49 |
| andor-1 | OOV | `src/sortedcontainers/sorteddict.py:134` | `if args and (args[0] is None or callable(args[0]` → `if args and (args[0] is None and callable(args[0` | REFUSED | 18.2 | - |
| notdrop-1 | OOV | `src/sortedcontainers/sortedlist.py:504` | `if not pos:` → `if pos:` | REFUSED | 48.7 | - |
| rangestart-1 | OOV | `src/sortedcontainers/sortedlist.py:2465` | `for pos in range(1, len(self._keys)):` → `for pos in range(len(self._keys)):` | REFUSED | 144.2 | - |
| lenm1-1 | OOV | `src/sortedcontainers/sortedlist.py:1053` | `max_pos = len(_maxes) - 1` → `max_pos = len(_maxes)` | REFUSED | 128.5 | - |

### rich

Scans: cmp 2 live of 4 tried, add 2 live of 2 tried, lit 0 live of 25 tried, andor 1 live of 2 tried, getdef 1 live of 1 tried, notdrop 1 live of 1 tried, rangestart 0 live of 0 tried, lenm1 1 live of 1 tried.

| case | vocab | site | mutation | verdict | seconds | suite runs |
|---|---|---|---|---|---|---|
| cmp-1 | in | `rich/highlighter.py:117` | `r"\b(?P<bool_true>true)\b|\b(?P<bool_false>false` → `r"\b(?P<bool_true>true)\b|\b(?P<bool_false>false` | REFUSED | 13.6 | - |
| cmp-2 | in | `rich/highlighter.py:118` | `r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?\` → `r"(?P<=number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?` | REFUSED | 252.3 | - |
| add-1 | in | `rich/markdown.py:368` | `console, options, number + index, last_number` → `console, options, number - index, last_number` | REFUSED | 17.4 | - |
| add-2 | in | `rich/panel.py:282` | `padding = left + right` → `padding = left - right` | REFUSED | 17.4 | - |
| andor-1 | OOV | `rich/pretty.py:786` | `if field.repr and hasattr(obj, field.name)` → `if field.repr or hasattr(obj, field.name)` | REFUSED | 21.3 | - |
| getdef-1 | OOV | `rich/console.py:808` | `term = self._environ.get("TERM", "").strip().low` → `term = self._environ.get("TERM").strip().lower()` | REFUSED | 66.7 | - |
| notdrop-1 | OOV | `rich/measure.py:141` | `if not renderables:` → `if renderables:` | REFUSED | 12.5 | - |
| lenm1-1 | OOV | `rich/table.py:638` | `last_column = column_index == len(self.columns) ` → `last_column = column_index == len(self.columns)` | REFUSED | 13.2 | - |

## 4. Replays: following the guard's own advice, and running the contended cases alone

| case | code | budget s (+flags) | verdict | seconds | suite runs | candidates rejected | guard's hint |
|---|---|---|---|---|---|---|---|
| arrow/add-1 | source tree | 300 | WRONG-GREEN | 220.8 | 12 | - |  |
| arrow/add-1 | pip fluidfix in venv | 300 | WRONG-GREEN | 117.4 | 25 | - |  |
| arrow/add-2 | pip fluidfix in venv | 300 | REFUSED | 297.9 | - | 73 | a candidate passes, but the search was cut short before it could be shown unique — shippin |
| arrow/cmp-1 | pip fluidfix in venv | 300 | REFUSED | 308.8 | - | 68 | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDGET — raise --escalat |
| arrow/cmp-2 | pip fluidfix in venv | 300 | REFUSED | 303.4 | - | 61 | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDGET — raise --escalat |
| click/cmp-1 | pip fluidfix in venv | 300 | REFUSED | 329.9 | - | 0 | --budget exhausted (300s) during the first pass — raise --budget, tighten taught-class sig |
| click/cmp-1 | source tree | 900 | REFUSED | 914.0 | - | 5 | --budget exhausted (900s) during the first pass — raise --budget, tighten taught-class sig |
| click/lit-1b | source tree | 300 | EXACT | 76.0 | 64 | - |  |
| click/lit-1b | pip fluidfix in venv | 300 | EXACT | 74.3 | 64 | - |  |
| python-sortedcontainers/add-1 | source tree | 300 | REFUSED | 242.8 | - | 96 | a candidate passes, but the search was cut short before it could be shown unique — shippin |
| python-sortedcontainers/cmp-2 | source tree | 300 | REFUSED | 253.1 | - | 97 | a candidate passes, but the search was cut short before it could be shown unique — shippin |
| python-sortedcontainers/cmp-2 | pip fluidfix in venv | 300 | EXACT | 61.9 | 67 | - |  |
| rich/add-1 | source tree | 300 | REFUSED | 302.9 | - | 135 | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDGET — but no POINTING |
| rich/add-1 | pip fluidfix in venv | 300 | REFUSED | 20.3 | - | 11 | every generated candidate was rejected by the suite (engine law: REFUTED -> HARVEST_COUNTE |
| rich/add-2 | source tree | 300 | REFUSED | 304.3 | - | 144 | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDGET — but no POINTING |
| rich/add-2 | pip fluidfix in venv | 300 | REFUSED | 20.2 | - | 11 | every generated candidate was rejected by the suite (engine law: REFUTED -> HARVEST_COUNTE |

## 5. The ladder: a model authors, the suite judges

Verdicts: EXACT = pristine bytes restored; WRONG-GREEN = the mutated line changed to something else and the
suite passed; SUSPECT = the suite passed but the mutated line is untouched (the author patched a different line,
a workaround, not a restoration); REFUSED = no proposal survived the suite.

### author: fable-5.1 — in-session author who had seen the bench log before authoring: an upper bound, not a blind measurement; tokens are characters/4

3/4 byte-exact, 0 wrong-green, 1 refused; tokens per case median 4131, total 19973.

| case | class | tier reached | verdict | tokens in | tokens out | tokens total | wall s | tier-1 rule check |
|---|---|---|---|---|---|---|---|---|
| click/andor-1 | andor | 1 | EXACT | 3900 | 119 | 4019 | 60.2 | ok: 1 matching line(s) |
| click/getdef-1 | getdef | 1 | EXACT | 3500 | 119 | 3619 | 72.7 | ok: 1 matching line(s) |
| click/lenm1-1 | lenm1 | 2 | REFUSED | 4059 | 184 | 4243 | 13.3 | signal matches no line in the suspect file |
| click/notdrop-1 | notdrop | 2 | EXACT | 7888 | 204 | 8092 | 72.9 | applier is a no-op on the matched line |

### author: gemma3:4b

0/3 byte-exact, 0 wrong-green, 3 refused; tokens per case median 11975, total 36364.

| case | class | tier reached | verdict | tokens in | tokens out | tokens total | wall s | tier-1 rule check |
|---|---|---|---|---|---|---|---|---|
| click/andor-1 | andor | 2 | REFUSED | 11373 | 602 | 11975 | 378.1 | signal matches no line in the suspect file |
| click/getdef-1 | getdef | 2 | REFUSED | 10219 | 169 | 10388 | 40.3 | signal matches no line in the suspect file |
| click/notdrop-1 | notdrop | 2 | REFUSED | 13801 | 200 | 14001 | 104.3 | applier is a no-op on every matched line |

### author: phi4-mini

0/4 byte-exact, 0 wrong-green, 4 refused; tokens per case median 9350, total 35700.

| case | class | tier reached | verdict | tokens in | tokens out | tokens total | wall s | tier-1 rule check |
|---|---|---|---|---|---|---|---|---|
| click/andor-1 | andor | 2 | REFUSED | 9508 | 483 | 9991 | 361.8 | signal matches no line in the suspect file |
| click/getdef-1 | getdef | 2 | REFUSED | 8504 | 204 | 8708 | 88.5 | bad signal: cannot refer to an open group at position 13 |
| click/lenm1-1 | lenm1 | 2 | REFUSED | 5114 | 216 | 5330 | 333.2 | applier is a no-op on the matched line |
| click/notdrop-1 | notdrop | 2 | REFUSED | 11512 | 159 | 11671 | 101.4 | signal matches no line in the suspect file |

### author: qwen3.5:4b

0/4 byte-exact, 0 wrong-green, 4 refused; tokens per case median 10124, total 39060.

| case | class | tier reached | verdict | tokens in | tokens out | tokens total | wall s | tier-1 rule check |
|---|---|---|---|---|---|---|---|---|
| click/andor-1 | andor | 2 | REFUSED | 10454 | 275 | 10729 | 411.7 | signal matches no line in the suspect file |
| click/getdef-1 | getdef | 2 | REFUSED | 9296 | 222 | 9518 | 101.4 | signal matches no line in the suspect file |
| click/lenm1-1 | lenm1 | 2 | REFUSED | 5572 | 258 | 5830 | 653.3 | ok: 1 matching line(s) |
| click/notdrop-1 | notdrop | 2 | REFUSED | 12795 | 188 | 12983 | 168.6 | ok: 1 matching line(s) |

### author: qwen3.5:4b — packet v1 (superseded: the packet never contained the defect line)

0/4 byte-exact, 0 wrong-green, 4 refused; tokens per case median 6306, total 22525.

| case | class | tier reached | verdict | tokens in | tokens out | tokens total | wall s | tier-1 rule check |
|---|---|---|---|---|---|---|---|---|
| click/andor-1 | andor | 2 | REFUSED | 6106 | 285 | 6391 | 349.9 | signal matches no line in the suspect file |
| click/getdef-1 | getdef | 1 | SUSPECT | 3339 | 184 | 3523 | 185.2 | ok: 1 matching line(s) |
| click/lenm1-1 | lenm1 | 2 | REFUSED | 6000 | 227 | 6227 | 71.1 | signal matches no line in the suspect file |
| click/notdrop-1 | notdrop | 2 | REFUSED | 6148 | 236 | 6384 | 200.4 | ok: 1 matching line(s) |

## 6. Teach once by hand, judged on another developer's repo (zero tokens)

One worked example per class met in this study, written by hand from the click incident (`taught/rules_session.py`, `taught/rules_session_b.py`), no model anywhere. The suite of each target repo judges the taught candidates on the same class as it occurs there.

Teaching examples restored: 5/5. Held-out cases (same class, another repo, zero tokens): 6/11 byte-exact, 0 wrong-green, 5 refused.

| case | class | role | verdict | seconds | suite runs | budget s | on refusal: was the correct line found? | guard's hint |
|---|---|---|---|---|---|---|---|---|
| arrow/andor-1 | andor | held-out (another repo) | REFUSED | 835.2 | - | 900 | correct line not among the rejected; guard reports a passing candidate held by CAPPED | a candidate passes, but the search was cut short before it could be sh |
| arrow/getdef-1 | getdef | held-out (another repo) | EXACT | 515.1 | 46 | 900 | - |  |
| arrow/lenm1-1 | lenm1 | held-out (another repo) | REFUSED | 837.9 | - | 900 | correct line not among the rejected; guard reports a passing candidate held by CAPPED | a candidate passes, but the search was cut short before it could be sh |
| arrow/notdrop-1 | notdrop | held-out (another repo) | EXACT | 172.5 | 3 | 900 | - |  |
| click/andor-1 | andor | teaching example | EXACT | 70.3 | 28 | 900 | - |  |
| click/getdef-1 | getdef | teaching example | EXACT | 60.1 | 6 | 900 | - |  |
| click/lenm1-1 | lenm1 | teaching example | EXACT | 354.8 | 3 | 900 | - |  |
| click/notdrop-1 | notdrop | teaching example | EXACT | 141.0 | 24 | 900 | - |  |
| python-sortedcontainers/andor-1 | andor | held-out (another repo) | EXACT | 31.5 | 19 | 900 | - |  |
| python-sortedcontainers/lenm1-1 | lenm1 | held-out (another repo) | EXACT | 64.5 | 17 | 900 | - |  |
| python-sortedcontainers/notdrop-1 | notdrop | held-out (another repo) | REFUSED | 47.8 | - | 900 | true line not reached | every generated candidate was rejected by the suite (engine law: REFUT |
| python-sortedcontainers/rangestart-1 | rangestart | teaching example | EXACT | 285.9 | 3 | 900 | - |  |
| rich/andor-1 | andor | held-out (another repo) | REFUSED | 904.1 | - | 900 | true line not reached | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDG |
| rich/getdef-1 | getdef | held-out (another repo) | EXACT | 228.0 | 9 | 900 | - |  |
| rich/lenm1-1 | lenm1 | held-out (another repo) | REFUSED | 904.5 | - | 900 | true line not reached | escalation budget exhausted (600s) with CAPPED still ruling RAISE_BUDG |
| rich/notdrop-1 | notdrop | held-out (another repo) | EXACT | 701.2 | 29 | 900 | - |  |

## 6b. Debugging mode: many searchers, one judge (prototype, no product change)

The router law's own domain is the sharding key: one guard per kind, each in its own clone, all in parallel, and a judge that runs no suite and rules with the engine law's outcomes over the guards' reports (`shards/judge.py`). Measured on the cases the serial guard found but could not finish (arrow's 6,000-line locale file) or reach (rich `pretty.py`).

| case | file | guards | judge's ruling | verdict | wall s (slowest guard) | cpu-sum s | green guards (kind) | distinct programs | held guards | serial guard, same dictionary |
|---|---|---|---|---|---|---|---|---|---|---|
| arrow/andor-1 | arrow/locales.py | 13 | SHIP | EXACT | 903.7 | 11689.4 | 4 | 1 | - | REFUSED in 835 s |
| arrow/lenm1-1 | arrow/locales.py | 13 | SHIP | EXACT | 930.8 | 12040.8 | 7 | 1 | - | REFUSED in 838 s |
| rich/andor-1 | rich/pretty.py | 13 | REFUSE (every guard's reason attached) | REFUSED | 917.3 | 11811.3 | - | 0 | - | REFUSED in 904 s |

## 7. What the measurements say

**Finding the file.** In a 302-file tree the true file ranked first 10/10 and the exact line came back in ~16 s. On the
real repos the ranking was right whenever the failure named a file; it went wrong in two measured ways, both fixed
today: a traceback frame inside the virtualenv was taken for project source (rich: every search died in pytest's own
code), and a rare-but-unrelated signal pointed the search at arrow's hub module (the SCARCE lane, now limited to
taught classes on the failing test's path — and still ambiguous with a multi-class dictionary, which no observation
can resolve).

**Repairing in vocabulary, zero tokens.** 7 of 22 real breaks restored byte-exact at 300 s in the pre-fix bench; the
refusals split into the honest kind (a passing candidate found, uniqueness unprovable under a capped view of a
3,000–6,000-line file), the hang kind (a mutant that also stalls a test makes every candidate cost the per-test
timeout), the bug kind (fixes 1–7), and my own harness's two out-of-class mutants. One wrong repair shipped (arrow: a
comparison flipped four lines above the fault, accepted by the suite) — the suite is the judge, so its blind spots are
the tool's.

**Escalating to a model.** Three 4B local models: 0 of 4 each on click, with the corrected full-sight packet; they
anchor on the crash line, not the guard above it, and their wrong proposals cost tokens (4k–14k per case), never a
wrong repair, because the same suite judges them. I (having seen the bench log) restored 3 of 4 on the same packets; that row is labelled for what it is. Haiku, run as a
sandboxed subagent that saw only the packet, wrote four answers (`cases/click/*/author_haiku-4.5/`): the right line on
and/or and `if not`, a workaround on `.get`, an invented line on `len-1`. They were never judged by the suite: the
judging lane was stopped at the user's request before it ran, so Haiku has no row in the table.

**Teaching once by hand.** One worked example per class from click, frozen (sha256 in `examples/taught-2026-09-16/`),
judged on the same classes in arrow, sortedcontainers and rich at the guard's advised 900 s: teaching examples 5/5,
held-out 6/11 byte-exact, 0 wrong, 5 refused with reasons (two found-but-held on a 6,000-line file, one doctest
pointer, one search-breadth miss, one ranking miss). Note the budget: a taught dictionary widens the search, and the
click `len-1` example needed 355–497 s because its file ranked fifth. Where it refuses, the table
says whether the correct line was found and held (uniqueness) or never reached.

**The PyPI release, side by side.** `fluidfix==0.15.0` installed in each clone, tier 0, 300 s, on nine in-vocabulary cases
(§4): same verdict as the source tree on click (hang refused, padded literal exact in 74 s) and on arrow's strictness and
second additive case (found, held); the same wrong repair on arrow additive 1 (117 s on the release, 221 s on the fixed tree:
the suite's blind spot, not the code's); rich additive 1 and 2 refused in 20 s on the release for the virtualenv bug and
refused at 300 s on the fixed tree for a ranking miss (`markdown.py` / `panel.py` never opened); sortedcontainers
strictness 2 exact in 62 s on the release, where the current tree, alone, holds it as found-but-unproven at 253 s — an open
difference (the tree is 0.15.0 plus the 2026-09-10 maintenance commits plus today's seven fixes; which change made the
uniqueness pass slower on this 3,000-line file is not diagnosed here). Net: the fixes remove a class of
false refusals (pytest's own code as a candidate) and one search defect (the escalation re-judging the first pass); they
do not change what the suite accepts.

**Where the clock goes.** Judging a candidate costs 2–5 s per suite run and 16–78 runs per repair; finding the file costs two
coverage runs, 5–40 s once; each file opened ahead of the right one costs a coverage pass, 30–90 s (click `len-1` spent ~300 of
355 s there); proving uniqueness after a green under a capped view costs more than 900 s on a 6,000-line file; a hanging
test costs 60 s per candidate; a wrong file first costs 50–500 candidates. None of it is the guard's own compute.

**Debugging mode, prototype.** Routed by kind — thirteen guards, one per shipped or taught class, each in its own clone, all
at once, a judge that runs no suite — the two arrow faults the serial guard had found and held in the 6,000-line locale
file were shipped byte-exact: only the matching kind's guard went green, one program, SHIP (§6b). The cost is honest and
large: 900–930 s wall for the slowest guard because thirteen suites shared twelve cores, and ~12,000 CPU-seconds per
incident. Rich and/or refused under the same contention with the ranking miss inherited by every shard. What routing buys
is exactly what the serial cost map predicted: one kind's candidates on a huge file fit the uniqueness pass; thirteen
kinds' do not.

**Seven product fixes came out of the run** (all applied, `fluidfix selfcheck` PASS): virtualenv paths are harness
paths; SCARCE from taught classes only, on the failing test's path; the refusal names the per-test timeout when the
red run hit one; the capped packet's sampler no longer repeats lines; an empty coverage report is "no coverage",
not a crash; and the escalation pass no longer re-judges the first pass's rejected candidates (before this, a fault
ranked 44th of 56 lines was unreachable at any budget).

**What was wrong with the measuring, and how it was handled.** My follow-up jobs and a second session's run shared
clones and CPU with the bench for parts of the evening; every affected row was discarded and re-measured alone, and
notes.md records each instance with times.

## 8. Not measured

- Claude Haiku / Sonnet / Opus and GPT as authors: no API key is available to this session and I will not enter
  one. `fuse.py --backend anthropic` is wired and runs the moment a key is set; a GPT backend would be ~15 lines.
- My own token counts are approximate (characters/4): I am not called through an API here.
