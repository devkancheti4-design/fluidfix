# 15-byte-exact-audit — is "byte-exact" literally true?

## 1. Target

Audit fluidfix's public byte-exactness claim: over 20 seeded defects, diff every
repaired file against the **pristine pre-defect original** byte for byte —
trailing whitespace, line endings, final newline, BOM, and file mode included.

The claim under test, `README.md:7` (and on the website):

> Every output is either a repair your suite accepts — measured **byte-exact in
> 26 of 26 accepted repairs on the benchmark** — or an explicit refusal.

## 2. Attack design

fluidfix's whole-file byte path is careful: `loop.py:182` reads with
`newline=""`, `raw = src.split("\n")` so `"\n".join(raw) == src` exactly,
`_write` (`loop.py:74`) writes with `newline=""`, and `open(path, "w")`
truncates in place so the inode and mode survive. Attacking *that* looked
unpromising.

The soft spot is one layer down. Whole-file fidelity is preserved, but the
**per-line appliers in `acts.py` are regex rewrites of a single line**, and a
regex that reorders capture groups reorders whatever those groups swept up —
trailing spaces, comments — along with the operands it meant to move. So the
hypothesis was:

> fluidfix is byte-exact on the *file* and byte-sloppy on the *line*. Put
> whitespace or a comment where an applier's `(.*)$` group can reach it and the
> shipped bytes will differ from the user's original even though the suite is
> green and the report says "repaired".

Two supporting hypotheses, both about bytes that never reach the law:

- `loop.py:342` pre-filters Python candidates with `compile(content, path,
  "exec")`. `compile()` of a **str** rejects `U+FEFF`; Python loading the same
  bytes from disk strips the BOM. A BOM file should therefore make every
  candidate "fail" without a single suite run.
- `localize.py:100` reads sources as strict UTF-8. A legally-declared latin-1
  source should raise rather than refuse.

Nothing below weakens fluidfix. No source edit, no monkeypatch, no
`FLUIDFIX_*` env var. The only non-default setting is `--suite-timeout 45`
(the documented flag; the 300s default only buys clock for non-terminating
candidates, which is a different target — see Attempt 0).

## 3. Attempts

20 fixtures, each a *pristine correct* module that is green, then one
mechanical fault injected as a pure byte edit and nothing else changed.
`audit.py`/`fixtures.py` (01–16) and `audit2.py`/`fixtures2.py` (17–20) build,
run `guard_once` exactly as `fluidfix guard` does, and diff the result against
the pristine bytes plus `st_mode`. Logs: `run1.log`, `run2.log`; machine
records: `results.json`, `results2.json`.

| # | fixture | awkward input | status | byte-exact |
|---|---------|---------------|--------|-----------|
| 01 | strictness, LF | control | repaired | yes |
| 02 | flipped-additive | **CRLF throughout** | repaired | yes |
| 03 | swapped-return-operands | **2 trailing spaces on the line** | repaired | **NO** |
| 04 | literal-off-by-one | **no final newline** | repaired | yes |
| 05 | minmax-swap | **tab indentation** | repaired | yes |
| 06 | strictness | **UTF-8 BOM** | **refused** | n/a (see 4.2) |
| 07 | strictness | **non-ASCII identifier `größe`, em-dash string** | repaired | yes |
| 08 | flipped-augmented-assign | — | repaired | yes |
| 09 | flipped-comparison | — | repaired | yes |
| 10 | flipped-boolean | — | repaired | yes |
| 11 | reversed-minus-operands | **3 trailing spaces on the line** | repaired | **NO** |
| 12 | literal-off-by-one | **CRLF + no final newline** | repaired | yes |
| 13 | flipped-additive | **file mode 0o755** | repaired | yes (mode kept) |
| 14 | literal-off-by-one | **zero-padded `\033` escape** | repaired | yes |
| 15 | strictness | **latin-1 declared source** | **crash** | n/a (see 4.4) |
| 16 | strictness | trailing ws on *neighbouring* lines, blank final line | repaired | yes |
| 17 | strictness | **CR-only (classic Mac) endings** | repaired | yes (see 4.5) |
| 18 | strictness | trailing ws **on the repaired line** | repaired | yes |
| 19 | swapped-return-operands | **trailing `# comment` on the line** | repaired | **NO — and wrong program** |
| 20 | reversed-minus-operands | CRLF, repaired line is the last line | repaired | yes |

**Totals: 20 fixtures, 18 accepted repairs, 15 of 18 byte-exact.**
Every pristine fixture was verified green before injection (`pre_green: true`
in both result files).

### Attempt 0 — a non-terminating candidate (aborted, not a finding)
The first draft of fixture 08 used `while k: ... k -= 1`. fluidfix flipped
`k -= 1` to `k += 1` and the candidate hung; the run cost the full 300s
`--suite-timeout` and was killed. **That is fluidfix behaving correctly** — a
bounded candidate, exactly as `oracle.py` documents — and it belongs to target
14, not here. The fixture was rewritten with a `for` loop and the audit run at
`--suite-timeout 45`.

### Attempt 1 — whole-file byte channel (DEFENDED)
CRLF (02, 12, 20), no final newline (04, 12), tabs (05), BOM bytes (06),
non-ASCII identifiers and an em-dash string (07), a zero-padded octal escape
(14), a `0o755` file (13), CR-only endings (17). **Not one of these was
corrupted.** Across all 20 fixtures the CRLF count, lone-LF count, lone-CR
count, final-newline flag, BOM flag and `st_mode` after the run are identical
to the pristine file. `.fluidfix/inflight.json` is cleared; the only repo
residue is an empty `.fluidfix/` directory.

### Attempt 2 — per-line appliers and trailing whitespace (SUCCEEDED: 03, 11)
See 4.1.

### Attempt 3 — per-line appliers and trailing comments (SUCCEEDED: 19)
See 4.3. This is the S1.

### Attempt 4 — the `compile()` pre-filter vs a BOM (SUCCEEDED: 06)
See 4.2.

### Attempt 5 — non-UTF-8 source (SUCCEEDED as a crash: 15)
See 4.4.

### Attempt 6 — trailing whitespace *on* a slice-based act's line (DEFENDED)
Fixture 18 puts the trailing spaces on the very line kind 0 rewrites.
`_flip_strictness` builds its candidate with `line[:i] + b + line[i+len(a):]`,
so everything outside the operator survives. Byte-exact. Likewise fixture 16
with trailing whitespace and a tab on *neighbouring* lines: untouched lines are
never reconstructed, only re-joined.

### Attempt 7 — `_dec_at`'s `x + 1` → `x` collapse (NOT REPRODUCED)
`acts.py:159-162` deletes the operator and its surrounding spaces when a
decrement reaches `0`. Code-reading says this breaks byte-exactness whenever
the pristine line genuinely reads `... + 0`, but no plausible fixture writes
`+ 0`, so this is reported as a code observation only, not a measured finding.

## 4. Outcome

### 4.1 — S3 FALSE CONFIDENCE: trailing whitespace destroyed on an accepted repair

**Reproduce** (builds a git repo whose HEAD holds the pristine file, then runs
the real binary):

```
cd research/adversarial-2026-09-07/15-byte-exact-audit
./rt 600 ../../../.venv/bin/python repro_cli.py        # log: repro_cli.log
```

**The diff fluidfix wrote** (`git diff` against the committed pristine file):

```
--- a/mod.py
+++ b/mod.py
@@ -2 +2 @@ def join2(a, b):
-    return a + b··          <- pristine, two trailing spaces
+    return a···+ b          <- shipped, spaces moved across the operator
```

fluidfix's own report:

```
mod.py: repaired line 2 in 4 suite runs (1.7s):
  - return b + a
  + return a   + b
```

Fixture 11 is the same defect in the other direction and adds a sharper fact:
`RepairResult.greens` held **both** spellings —

```
['    return b    - a',      <- shipped
 '    return b - a   ']      <- byte-identical to the user's original
```

— and `_rule` ships `greens[0]`, first-found order. **fluidfix had the
byte-exact restoration in hand and shipped the other one.**

**Mechanism.** `acts.py:188` —
`re.match(r"^(\s*return\s+)(.*?)(\s(?://|[-+*])\s)(.*)$", line)` — group 4 is
`(.*)$`, so it swallows the line's trailing whitespace along with the right
operand, and the rewrite `g1+g4+g3+g2` deposits it in the middle.

**Classification: actuation** (with a *wording* aggravator).
- Observation byte passed: `BUILT=1, AMB=0, CAPPED=0` → `situation(...) = 513`
  (`0b1000000001`), law returns **SHIP**.
- That ruling is correct: a green candidate exists and it is the only program
  found. The law is not at fault.
- The body then wrote bytes that are not the minimal edit the act claims to be
  ("operands in the wrong order"), so the actuation differs from the ruling's
  intent.
- *Wording aggravator:* `loop.py:69-70` prints `old_line.strip()` /
  `new_line.strip()`, so the diff shown to the user **cannot** display the
  trailing whitespace it deleted. Worse, fluidfix computes the honest bit —
  `_restored_original()` returns **False** here, verified directly on the
  reproduction repo — and `restored_original` is never printed anywhere in
  `cli.py`. The tool measures its own headline claim and then hides the answer.

### 4.2 — S4 DENIAL + S3 FALSE CONFIDENCE: a UTF-8 BOM makes every candidate "fail"

**Reproduce:**

```
./rt 300 ../../../.venv/bin/python repro_bom.py        # log: repro_bom.log
```

Two identical repos, one with `EF BB BF` prepended. Both import and run fine
(`import ok: 3` for each). Without the BOM: `repaired line 4 in 6 suite runs`.
With the BOM:

```
[repro-bom] status=refused suite_runs=None
  tried '        if x > t:'   why='does not compile: invalid non-printable
                                  character U+FEFF (mod.py, line 1)'
  ... 5 candidates, all the same reason
```

**The correct repair was generated and thrown away, and no suite run was ever
paid.** The refusal text is false twice over:

```
REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py).
  hint: every generated candidate was rejected by the suite (engine law:
        REFUTED -> HARVEST_COUNTEREXAMPLE) — the refusal report lists each one
        with the test that killed it
```

- "outside the taught vocabulary" — it is kind 0, and fixture 01 is the same
  defect repaired byte-exact.
- "rejected by **the suite**" / "the test that killed it" — no suite ran on any
  candidate; `loop.py:342-352` killed them all before `oracle.check`.

**Classification: observation.**
- Observation byte passed: `REFUTED=1` → `situation(REFUTED=True) = 576`
  (`0b1001000000`) → **HARVEST_COUNTEREXAMPLE**. Correct act for that byte.
- The bit was measured wrongly. `compile(str_with_U+FEFF)` is not a
  measurement of "does this file compile" — Python strips the BOM when loading
  from disk. `BUILT` was never even given a chance to be measured.
- On the correct byte, `BUILT=1` → `513` → **SHIP**, and the shipped line would
  have been byte-exact.

No corruption: the file is left holding the defect exactly (`unchanged_from_defect: true`).

### 4.3 — S1 WRONG REPAIR SHIPPED: a trailing comment swallows the expression

**Reproduce:** `repro_cli.py`, case `cli-19-comment` (same command as 4.1).

**The diff fluidfix wrote:**

```
--- a/mod.py
+++ b/mod.py
@@ -2 +2 @@ def delta(a, b):
-    return a - b  # signed difference
+    return a  # signed difference - b
```

fluidfix reports `repaired line 2 in 3 suite runs`. The shipped program is
**wrong**: `- b` is now inside the comment.

```
delta(5, 0) = 5   (the one assertion the suite pins — green)
delta(9, 2) = 9   correct is 7
delta(1, 1) = 1   correct is 0
```

**Mechanism.** The same `(.*)$` group as 4.1. Kind 2 claims to fix "operands in
the wrong order"; on a commented line it instead **deletes an operand by
commenting it out**. The fault class fluidfix believes it is applying and the
byte transform it actually applies are different classes.

**Two greens were found, and they are two different programs:**

```
greens = ['    return a  # signed difference - b',   <- shipped; returns a
          '    return b + a  # signed difference']   <- returns a + b
```

**Classification: observation.**
- Observation byte passed: `BUILT=1, AMB=0, CAPPED=0` → `513` → **SHIP**.
- `AMB` was measured **False** while two genuinely different programs were
  green. `loop.py:219` computes `AMB = set_amb or len(sites) > 1`: both greens
  sit at line 2, and they came from two *different candidate sets*, so
  `set_amb` is False and `len(sites) == 1`. This is attack surface C, reached
  from a new direction — the second program here exists only because the act
  is not comment-safe.
- On the correct byte, `BUILT=1, AMB=1` → `situation(...) = 515`
  (`0b1000000011`) → **ADD_STATE**: refuse and ask for one pinning test. The
  ruling was available and right; the situation was measured wrongly.

**Honesty note.** This S1 is joint: the suite is weak (one assertion, with
`b = 0`), which is target 03's territory. What belongs to *this* target is that
the byte transform manufactured the wrong program in the first place — a
comment-safe applier would never have offered `return a` as a candidate for a
"swapped operands" fault, and the search would have shipped the correct
`return a - b  # signed difference`, byte-exact.

### 4.4 — S4 DENIAL: a latin-1 source crashes the guard instead of refusing

Fixture 15 is a legal `# -*- coding: latin-1 -*-` module with one `0xE9` byte.
`localize.py:100` reads sources as strict UTF-8 and the exception escapes
`guard_once` uncaught:

```
File ".../fluidfix/localize.py", line 101, in build_packet
    src = f.read()
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 38
```

Reproduce: `./rt 300 ../../../.venv/bin/python audit.py 15` (see `run1.log`).
Not a corruption — the file is untouched — but the contract is "a repair or an
explicit refusal", and a traceback is neither. Note `guard.py:245` and
`coracle.py:378` already read with `errors="replace"`; `localize.py` does not.
**Classification: observation** — the file was never measured at all.

### 4.5 — S3 (minor): CR-only file, "repaired line 1", whole file printed as one line

Fixture 17. `loop.py:184` splits on `"\n"` only, so a classic-Mac CR-only file
is **one line** to fluidfix. The bytes came out exact (the slice-based act
preserves everything), but the report names the wrong line:

```
./rt 300 ../../../.venv/bin/fluidfix guard work/cli-17-cronly \
    --python ../../../.venv/bin/python --suite-timeout 45   # repro_cronly.log

mod.py: repaired line 1 in 6 suite runs (3.3s):
  - def count_above(xs, t):^M    n = 0^M    for x in xs:^M        if x >= t:^M ...
  + def count_above(xs, t):^M    n = 0^M    for x in xs:^M        if x > t:^M ...
```

The edit is on the file's 4th logical line, reported as line 1, with the entire
file dumped as the before/after "line". **Classification: wording** — the
outcome was right and the report described it wrongly.

## 5. What defended

- **The whole-file byte channel.** `newline=""` on both read (`loop.py:182`)
  and write (`loop.py:74-76`), plus `raw = src.split("\n")` / `"\n".join(...)`,
  round-trips CRLF, lone LF, CR-only, a missing final newline and a BOM's bytes
  perfectly. 20/20 fixtures kept their exact EOL and BOM profile.
- **`open(path, "w")` truncates in place**, so the inode and permission bits
  survive: the `0o755` fixture came back `0o755`. 20/20 modes preserved.
- **Per-line ending reconstruction.** `body = raw[i].rstrip("\r")` /
  `ending = raw[i][len(body):]` (`loop.py:281-282`) re-attaches the exact
  ending, so the CRLF fixtures repaired byte-exact including on the last line.
- **Untouched lines are never rewritten**, only re-joined — fixture 16's
  trailing whitespace and stray tab on neighbouring lines survived.
- **Slice-based appliers are byte-safe.** `_flip_strictness`,
  `_flip_comparison`, `_swap_minmax`, `_flip_augmented`, `_flip_boolean` and
  `_reduce_literal` all build `line[:i] + new + line[j:]` and were byte-exact on
  every fixture, including with trailing whitespace *on the repaired line*
  (18). `_dec_at`'s zero-padding rule kept `\034` → `\033` at full width (14).
- **Rollback held everywhere.** The two non-repairs (06, 15) left the file
  holding exactly the injected defect, byte for byte — including the run that
  died inside `build_packet` with an uncaught `UnicodeDecodeError` (15).
  `inflight.json` is gone from all 24 `.fluidfix/` directories under `work/`;
  only the empty directory remains. (Kill-window behaviour is target 11's, not
  measured here.)
- **The group-reordering appliers are the whole attack surface.** Only
  `_swap_return_operands` (03, 19) and its overlap with `_reverse_minus_operands`
  (11) failed. Every other act held.

**Suggested fix, report-only (no `src/` edit made):** two independent changes.
(a) make the group-reordering appliers operate on the code *before* any trailing
comment and re-append it, and split off trailing whitespace the way
`_reverse_minus_operands` already does with its `(\s*)$` tail group — that alone
kills 4.1 and 4.3. (b) In `_rule`, when several greens are in hand, prefer the
one for which `_restored_original` is True instead of `greens[0]`; fixture 11
shows the byte-exact green was already there. And print `restored_original` in
the CLI: it is the claim the README makes, computed and discarded.

## 6. Verdict

fluidfix's byte-exactness is real at the file level (EOL, BOM, final newline and
file mode survived 20/20 awkward inputs) and false at the line level: **15 of 18
accepted repairs were byte-exact, and the three misses all come from the two
appliers that reorder regex capture groups — one of which (`_swap_return_operands`
on a commented line) shipped a silently wrong program as "repaired" (S1), with a
BOM file additionally refused for a reason the run does not support (S3/S4).**

---

### Files

- `ATTACK.md` — this report
- `rt` — `nice -n 15` + perl-`alarm` timeout wrapper (no coreutils `timeout` here)
- `fixtures.py`, `audit.py`, `run1.log`, `results.json` — fixtures 01–16
- `fixtures2.py`, `audit2.py`, `run2.log`, `results2.json` — fixtures 17–20
- `repro_bom.py`, `repro_bom.log` — finding 4.2, isolated
- `repro_cli.py`, `repro_cli.log` — findings 4.1 and 4.3 through the real binary, in git
- `repro_cronly.log` — finding 4.5
- `work/` — every victim repo, left as fluidfix left it

Nothing outside this directory was written. `git status` on the fluidfix repo
shows only `research/` untracked; the `CHANGELOG.md` modification predates this
agent and was not touched. No git state was changed anywhere except inside
`work/cli-*`, which are throwaway repos this audit created.
