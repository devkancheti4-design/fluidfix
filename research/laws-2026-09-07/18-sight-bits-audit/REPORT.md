# 18-sight-bits-audit

## 1. Target
For each of the SIGHT law's eight bits (FRAMED / SCARCE / LITERAL / FAILONLY /
NAMED / TOUCHED / SMALL / UBIQUITOUS): which the body actually measures, by
what code, and which are never set in practice.

## 2. Method

Read, in `/Users/kanchetidevieswar/neo/fluidfix/`:

- `src/fluidfix/sight.py` — the law and its specification docstring.
- `src/fluidfix/guard.py:118-300` — `find_candidate_files()`, the only place in
  the body that calls the law (`guard.py:280`). Confirmed sole call site:

      $ grep -rn "observe_bits\|from .sight" src --include="*.py"
      src/fluidfix/cli.py:501:    from .sight import sight as _sight     # selfcheck only
      src/fluidfix/guard.py:216:  from .sight import observe_bits as _sight_bits, sight as _sight
      src/fluidfix/guard.py:280:      return _sight(_sight_bits(

- `src/fluidfix/acts.py` `KINDS` — the nine signal regexes SCARCE reads.

Scripts, all in this directory, all run through `./run300.sh` (`nice -n 15`
plus a 300 s alarm; macOS has no `timeout`):

| script | what it does | output |
|---|---|---|
| `sight_probe.py` | temporarily rebinds `fluidfix.sight.sight` to a recorder that logs the byte the body hands the law, then calls the real law. Nothing in `src/` is edited; the ranking is exactly what it would have been unobserved. | `probe_*.txt` |
| `guard_run.py` | one real `guard_once()` pass on a **copy** of a fixture, same recorder | `guard_*.txt` |
| `reachable_bytes.py` | static reachability of the 256 bytes | `reachable_bytes.txt` |
| `bit_influence.py` | per-bit ruling-change census over all 256 and over the law-path-reachable bytes | `bit_influence.txt` |
| `make_fixtures.py` | fixtures f1-f4 | `fixtures/` |
| `make_f5.py`, `make_f5b.py` | FRAMED basename-collision A/B | `fixtures/f5*`, `probe_f5*.txt`, `guard_f5*.txt` |
| `make_f6.py` | TOUCHED repo-root vs subdirectory A/B (creates two throwaway git repos **inside this directory only**) | `probe_f6_touched.txt` |
| `make_f7.py` | a failure with a real in-root traceback frame | `probe_f7_realframe.txt` |

No file outside this directory was written. No git command that changes state
was run against any existing repository.

## 3. Findings

### F1. The law is never consulted when the failure names a project file — so FRAMED as specified is unreachable at the law's input.

`guard.py:145-150` returns the traceback frame list *before* the law is
reached:

    ordered.reverse()
    if ordered:
        ...
        return ordered[:limit]

`ordered` holds every `*.py` mention in the failing output that (a) resolves
under `oracle.root`, (b) is an existing file, and (c) is not a test path
(`guard.py:131-144`). Fixture `f7_realframe` is exactly the case the FRAMED
bit describes:

    $ ./run300.sh .venv/bin/python sight_probe.py fixtures/f7_realframe 4
    == failing output lines the ranker's regexes read ==
        tests/test_ratio.py:5:
        pkg/geom.py:2: ZeroDivisionError
        FAILED tests/test_ratio.py::test_ratio - ZeroDivisionError: division by zero

    == sight() calls: 0  (0 means the law was never consulted) ==

    == order returned by find_candidate_files ==
       1. pkg/geom.py

Zero calls. The file order in the FRAMED case is decided by the body
(deepest-frame-first, `guard.py:141-145`), not by the law.

### F2. FRAMED, on the path where the law *is* consulted, measures basename collision — and it fires, on the wrong file.

`guard.py:218-219` rebuilds a *separate* set from the same text, keeping only
basenames and applying none of the three filters above:

    framed_files = {os.path.basename(m.group(1))
                    for m in re.finditer(r"([\w./\\-]+\.py)[\":,]", clean)}

and `guard.py:281` asks `framed=os.path.basename(rel) in framed_files`.

Fixture `f5_framed_coincidence` is a package whose failing test raises
`json.JSONDecodeError`. The traceback therefore names two **stdlib** files —
`json/__init__.py` and `json/decoder.py` — which are outside the root and are
dropped from `ordered`, so the law path is taken. The package contains a
`pkg/decoder.py` that is a decoy: no defect, and executed so broadly that its
specificity is 0.13 (UBIQUITOUS). Every `acts.KINDS` signal was made to match
all six modules, so SCARCE cannot fire for anyone; the failure is not an
assert, so LITERAL cannot fire either. FRAMED is the only POINTING bit in the
fixture:

    $ ./run300.sh .venv/bin/python sight_probe.py fixtures/f5_framed_coincidence 8
    == sight() calls: 6 ==
    file                         byte  prio   spec n_fail  bits
    pkg/__init__.py                73     0   1.00      9  FRAMED|FAILONLY|SMALL
    pkg/decoder.py                193     0   0.13      9  FRAMED|SMALL|UBIQUITOUS
    pkg/fmtx.py                    72     2   1.00      8  FAILONLY|SMALL
    pkg/geom.py                    72     2   1.00     14  FAILONLY|SMALL     <- the defect
    ...
    == order returned by find_candidate_files ==
       1. pkg/__init__.py
       2. pkg/decoder.py
       3. pkg/geom.py
    == evidence dict ==
       lanes[FRAMED]: ['pkg/__init__.py', 'pkg/decoder.py']

`f5b_no_collision` is the identical fixture with the decoy renamed
`pkg/dcodr.py` — same defect, same coverage shape, same ballast, only the
basename changes:

    $ ./run300.sh .venv/bin/python sight_probe.py fixtures/f5b_no_collision 8
    pkg/dcodr.py                  192     6   0.13      9  SMALL|UBIQUITOUS
    == order returned by find_candidate_files ==
       1. pkg/__init__.py
       2. pkg/geom.py
       ...
       6. pkg/dcodr.py

Byte 193 -> priority 0 (opened 2nd) versus byte 192 -> priority 6 (opened
last), caused by a filename coincidence with a stdlib module. The true defect
moves from 3rd to 2nd. The `evidence` dict reports the decoy under
`lanes[FRAMED]`, i.e. a refusal on this repo would tell the user the traceback
pointed at a file it never named.

Note also `pkg/__init__.py`: it carries FRAMED in **f5, f5b, f3_framed and
f3b** because any stdlib or site-packages `__init__.py` in a traceback
collides with every Python package's `__init__.py`.

Across all fixtures in this directory the FRAMED bit was set on 5 distinct
file/observation pairs. **Zero** of them were a traceback frame naming that
file; all five were basename collisions with an out-of-root path.

### F3. Every byte carrying FRAMED is priority 0, and no bit can demote it.

    $ ./run300.sh .venv/bin/python bit_influence.py
    == priorities emitted ==
      all 256 inputs                : [0, 2, 3, 4, 5, 6, 7]
      FRAMED-carrying bytes         : [0]

    == all 256 inputs: 256 bytes ==
    bit         flips ruling   of  best promotion  ever demotes
    FRAMED                32  128              -7             0
    SCARCE                32  128              -7             0
    LITERAL               32  128              -7             0
    FAILONLY              16  128              -4             0
    NAMED                  8  128              -3             0
    TOUCHED                4  128              -2             0
    SMALL                  2  128              -1             0
    UBIQUITOUS            16  128               0            16

This is the law behaving exactly as authored (R1/R2: a POINTING bit zeroes the
`gate`, so the ubiquity penalty and all circumstantial terms drop out). It is
also why a mismeasured FRAMED is the most expensive bit to get wrong: it is a
guaranteed 7-step promotion that nothing downstream can undo.

### F4. TOUCHED is measured against the wrong frame of reference whenever the project root is not the repository root.

`guard.py:220-227` runs `git -C oracle.root log -40 --name-only --format=`,
whose output paths are relative to the **repository** root, and `guard.py:286`
tests `rel in recent_files`, where `rel` is relative to **`oracle.root`**.

    $ ./run300.sh .venv/bin/python make_f6.py
    f6a_repo_root: project root = .../fixtures/f6a_repo_root
       git -C <project root> log --name-only -> ['mod.py', 'test_mod.py']
    f6b_subdir: project root = .../fixtures/f6b_subdir/proj
       git -C <project root> log --name-only -> ['proj/mod.py', 'proj/test_mod.py']

Identical sources, identical one-commit history that touched `mod.py`:

    f6a_repo_root:  mod.py  byte 122  prio 0  SCARCE|FAILONLY|NAMED|TOUCHED|SMALL
    f6b_subdir:     mod.py  byte  90  prio 0  SCARCE|FAILONLY|NAMED|SMALL

TOUCHED silently reads 0 in the subdirectory layout. A related leak: a project
with no `.git` of its own inherits whatever repository encloses it —

    $ git -C fixtures/f5_framed_coincidence rev-parse --show-toplevel
    /Users/kanchetidevieswar/neo/fluidfix

so `recent_files` there is fluidfix's own last 40 commits. The `except
Exception: recent_files = set()` at `guard.py:226-227` catches a missing git
binary, not a wrong or absent repository, so both failures are silent.

### F5. SCARCE's "repo-wide" scarcity is measured over the *candidate set*, not the repo, and the set can be smaller than the threshold.

`guard.py:245-249` reads bodies only for `{t[3] for t in ranked2}` — the files
the failing test executes — and `guard.py:271-273` fires SCARCE when a signal
matches `0 < len(hits) <= 2` of those. The comment at `guard.py:264-267` says
"only one or two files repo-wide". Consequence, measured:

    fixtures/f1_canonical  (1 candidate file)
      kind  0 strictness   '[<>]=?'   1 ['mod.py']  <- SCARCE
      kind  1 literal-off-by-one '\d'  1 ['mod.py']  <- SCARCE
      kind  9 flipped-augmented-assign '[-+]=(?!=)' 1 ['mod.py']  <- SCARCE
      kind 10 flipped-comparison-direction  1 ['mod.py']  <- SCARCE
      mod.py  byte 90  prio 0  SCARCE|FAILONLY|NAMED|SMALL

    fixtures/f5_framed_coincidence  (6 candidate files, same signals)
      kind  0 strictness   '[<>]=?'   6 [...]        (no SCARCE)
      lanes[SCARCE]: []

With at most two candidates SCARCE fires unconditionally for every one of
them, so a POINTING bit — which suppresses UBIQUITOUS and all circumstantial
evidence — carries no information at all and the whole ranking collapses to
priority 0, handing the order to the caller's tie-break. In `f2_multi`
(7 candidates) four files land on priority 0 for the same reason.

### F6. LITERAL is blind to single-digit literals.

`guard.py:237-242` harvests `re.findall(r"\d{2,}", ...)` from assert lines.
Measured, same probe script, two fixtures:

    f1_canonical:  E  assert 3 == 1        -> lanes[LITERAL]: []
    f2_multi:      E  assert 31 == 40      -> lanes[LITERAL]: ['pkg/consts.py', 'pkg/mid.py']

The single most common real defect class in the coordinator's scan is
off-by-one, whose assertion very often prints one-digit numbers. On those the
LITERAL lane cannot fire by construction.

### F7. Complete bit-by-bit audit table.

| bit | measured at | what the body actually reads | classification | observed set? |
|---|---|---|---|---|
| FRAMED | `guard.py:281`, set built `218-219` | basename of any `*.py` path anywhere in the failing output, unfiltered | **mismeasured** — spec says "the failing traceback names this file"; the true-frame case never reaches the law (F1), and what does reach it is a basename collision (F2) | yes, 5 times, 0 of them true frames |
| SCARCE | `guard.py:282`, set built `264-274` | a `KINDS` signal regex matching 1-2 of the *candidate* files | **approximated** — candidate set, not repo (F5); hardcoded threshold 2 | yes (f1, f2, f3, f3b) |
| LITERAL | `guard.py:283`, `237-255` | a >=2-digit number from an assert line occurring in 1-2 candidate bodies | **approximated** — hardcoded `\d{2,}` and threshold 2 (F6) | yes (f2 only) |
| FAILONLY | `guard.py:284` | `specificity >= 0.9`, specificity from two coverage runs (`166-191`) | **measured**, hardcoded threshold 0.9 | yes (most fixtures) |
| NAMED | `guard.py:285`, tokens `181-184`, `278-279` | >=3-letter token shared between the candidate's basename and the failing test module name | **measured**, hardcoded min token length 3 | yes (f1, f2, f3, f6) |
| TOUCHED | `guard.py:286`, set built `220-227` | `rel` present in `git log -40 --name-only` output | **mismeasured in common layouts** (F4); hardcoded depth 40 | yes (f1_git, f2, f6a) |
| SMALL | `guard.py:287` | `0 < n_fail < 80`, `n_fail` = executed lines under `--lf` (`172`); `n_fail > 0` already guaranteed by `188-189`, so the bit is only `n_fail < 80` | **measured**, hardcoded threshold 80 | yes (every fixture) |
| UBIQUITOUS | `guard.py:288` | `specificity < 0.25` | **measured**, hardcoded threshold 0.25 | yes (f2 `big.py`, f5 `decoder.py`) |

All eight bits were observed set at least once. None is dead code. But no bit
is measured entirely as its specification reads: the thresholds (2, 2, 0.9,
40, 80, 0.25 and `\d{2,}`) are numbers the body owns, not observations the law
was given.

### F8. Byte reachability.

    $ ./run300.sh .venv/bin/python reachable_bytes.py
    bytes the body can never build (FAILONLY & UBIQUITOUS): 64
    bytes buildable at all:                               192
      of which FRAMED set (only via basename coincidence): 96
      of which honestly measurable (FRAMED clear):         96
    priorities the honest bytes reach: [0, 2, 3, 4, 5, 6, 7]

FAILONLY (`spec >= 0.9`) and UBIQUITOUS (`spec < 0.25`) are two predicates on
one number and cannot both hold — 64 of the 256 inputs are structurally
unbuildable by this body. Priority 1 is never emitted by the law itself (the
docstring records this as reserved).

## 4. Lanes

Reached by this work, with a measured observation byte:

- POINTING/FRAMED — reached only in its mismeasured form (bytes 65, 73, 75,
  193). Reached as specified: **never**, and structurally cannot be (F1).
- POINTING/SCARCE — reached (bytes 66, 74, 82, 90, 122).
- POINTING/LITERAL — reached (bytes 6, 12).
- circumstantial FAILONLY, NAMED, TOUCHED, SMALL — all reached (bytes 72, 90,
  96, 122).
- penalty UBIQUITOUS — reached (bytes 192, 193).
- priority classes 0, 2, 4, 5, 6 were produced by real fixtures. Priorities 3
  and 7 were **not** produced by any fixture here; both are reachable per
  `reachable_bytes.py`, they simply need a candidate with almost no evidence
  plus the penalty.
- Priority 1 is emitted by no input; the docstring says the slot is reserved.

Never reached, and why:

- The law itself on any repo whose failure produces an in-root non-test
  traceback frame — `guard.py:146` returns first. That is the majority shape
  of a crashing failure; the law only governs assertion-style failures.
- `FAILONLY & UBIQUITOUS` together — algebraically impossible for one
  specificity (64 bytes).

## 5. Potential

- **FRAMED measured as specified.** The observation that would make the
  specified lane reachable already exists three lines above the law: the
  `ordered` list at `guard.py:145`. Passing it into the ranking (`framed = rel
  in ordered`) instead of returning early would put every candidate through
  one ranking with real POINTING evidence, and would remove the basename
  collision entirely. Measured value on `f5`: the true defect moves from rank
  3 to rank 2 and the decoy from rank 2 to rank 6 (F2). Value in **suite
  runs** on `f5`: **zero** — both `f5` and `f5b` repaired `pkg/geom.py` in 8
  suite runs (`guard_f5_framed_coincidence.txt`, `guard_f5b_no_collision.txt`),
  because the decoy is small enough that the budget swallowed it. The cost on
  a repository the size of Box2D or click is **unmeasured** here.
- **A SCARCE denominator.** The lane needs to know how many files it looked
  at. With <=2 candidates it fires for everything (F5). A bit such as
  `WIDE_CANDIDATE_SET` (candidate count > 2), or measuring hits repo-wide as
  the comment claims, would restore its discriminating power. Effect size:
  **unmeasured**.
- **A TOUCHED that is repo-root aware.** `git -C root rev-parse --show-prefix`
  gives the prefix needed to reconcile the two path frames, and
  `--show-toplevel` detects the "enclosing foreign repository" case.
  Frequency in real repositories: **unmeasured**. Effect on the ruling when it
  does flip: TOUCHED changes the priority on 4 of 48 law-path-reachable byte
  pairs, best promotion 2 steps (`bit_influence.txt`).
- **LITERAL on one-digit literals.** Widening `\d{2,}` to `\d+` would let the
  lane fire on off-by-one assertions; whether the resulting hits stay under
  the <=2-file discrimination test is **unmeasured**.

## 6. Defects

1. **FRAMED — observation.** The body measures "some `.py` path in the failing
   output shares this file's basename" (`guard.py:218-219`, `281`) and hands it
   to the law as the bit the law documents as "the failing traceback names this
   file". Evidence: F2, the `f5`/`f5b` A/B — byte 193 vs 192, priority 0 vs 6,
   from a rename and nothing else. The ruling on byte 193 is correct: the law
   was told the failure pointed at that file. Not a ruling defect.
2. **FRAMED — actuation/reachability.** The lane the law was given first is
   the one the caller never lets it see: `guard.py:146` returns the frame list
   before the law is consulted, so the law rules only on failures where FRAMED
   cannot legitimately be true. Evidence: F1, `sight() calls: 0` on
   `f7_realframe`.
3. **TOUCHED — observation.** Repository-relative paths compared against
   root-relative paths (`guard.py:221-225` vs `286`). Evidence: F4, byte 122
   vs 90 for the same file with the same history. Silent: the `except` at
   `guard.py:226` cannot see a wrong repository.
4. **SCARCE — wording, and observation.** The comment at `guard.py:264-267`
   says "repo-wide"; the code measures over the candidate set only
   (`guard.py:245-249`). With <=2 candidates the POINTING bit is set for every
   file unconditionally. Evidence: F5.
5. **LITERAL — observation.** `\d{2,}` (`guard.py:238`) makes the lane blind
   to single-digit assertion literals, i.e. to much of the most common defect
   class. Evidence: F6.

No defect found in any SIGHT **ruling**. On every byte recorded here the law's
output matches its published specification, and the exhaustive
specification/R1/R2/R3 check in `cli.py:501-520` (`fluidfix selfcheck`) covers
all 256 inputs.

## 7. Verdict
All eight SIGHT bits are set somewhere in practice, but three are mismeasured
by the body — FRAMED fires only on out-of-root basename collisions and is
structurally never reachable in its specified form, TOUCHED silently reads 0
whenever the project root is not the git root, and SCARCE's "repo-wide"
scarcity is measured over the candidate set — while the law's rulings on the
bytes it was handed were correct in every case measured.
