# 13-stale-and-symlink

## 1. Target

`COracle.stale_binary()` and the file-writing path (`loop._write`, the candidate
reassembly in `loop.repair`, `loop.recover_inflight`) under hostile *file
shapes*: symlinks, hardlinks, read-only modes, CRLF, no trailing newline, a
UTF-8 BOM, a non-UTF-8 encoding, and a poisoned mtime.

## 2. Attack design

fluidfix's product claim is byte-exact restoration inside the repo it was
pointed at. Three properties have to hold for that claim, and all three are
computed by *code*, not by the law:

1. **Containment.** `guard.find_candidate_files` (guard.py:137) accepts a file
   only if `os.path.normpath(full).startswith(oracle.root + os.sep)`. That is a
   **lexical** test. `_write` (loop.py:75) then does
   `open(path, "w", encoding="utf-8", newline="")`, which **follows symlinks**.
   Lexical containment plus a link-following writer is the classic escape: any
   name inside the root that resolves outside it passes the check and is then
   written through.
2. **Byte preservation.** The single-line path is careful (`body =
   raw[i].rstrip("\r")`, `ending = raw[i][len(body):]`, reattached at
   loop.py:329). The `SpanEdit` path is not symmetric with it: loop.py:320 keeps
   **only the last** line's ending (`cend = raw[e_-1][...]`) and takes every
   interior line ending from `cand.text`, which is LF-joined. On a CRLF file an
   N-line span must therefore lose N-1 CRs.
3. **The decode/encode round trip.** The file is read as `encoding="utf-8"` and
   candidates are gated by `compile(content, path, "exec")` (loop.py:342). A
   `.py` file that CPython *imports* fine but that a `str` cannot carry — a
   UTF-8 BOM — makes `compile()` on the string reject a candidate that is
   perfectly valid as a file. That converts a repairable defect into a refusal
   whose stated reason is false.

And for staleness: `_newest_source_mtime` (coracle.py:141) walks **every**
`*.c/*.h/*.cpp/...` under the root — compiled or not — and `os.path.getmtime`
follows file symlinks. It never checks that the value is in the past. Any one
file with a future timestamp should therefore pin `stale_binary()` to True
permanently, and the refusal's advised remedy (rebuild) cannot clear it.

Everything below runs the shipped binary with default settings. No fluidfix
source was edited, nothing was monkeypatched, no `FLUIDFIX_*` variable was set.
The one dictionary used (`dict_span.py`) registers a class in the reserved user
slot 4, which is the documented teaching path.

## 3. Attempts

All fixtures carry the *same* defect in the *same* tiny package; only the file
shape varies. `f01-plain` is the control.

| # | fixture | shape | result |
|---|---------|-------|--------|
| 1 | `f01-plain` | LF, ordinary file | **repaired**, 1 byte changed, mode+inode preserved — control |
| 2 | `f02-no-eol` | no trailing newline | **repaired**, `cmp -l` reports exactly one differing byte; no newline appended. Defence held |
| 3 | `f03-crlf` | CRLF throughout, single-line repair | **repaired**, CR count 7 before / 7 after, length identical. Defence held |
| 4 | `f04-bom` | UTF-8 BOM | **REFUSED — attack landed (S4 + S3)** |
| 5 | `f05-readonly` | source mode 0444 | **crash** — uncaught `PermissionError`, exit 1 (S4, low). Tree byte-identical, journal cleared |
| 6 | `f06-mode755` | executable source | **repaired**, mode still `-rwxr-xr-x`. Defence held |
| 7 | `f07-hardlink` | two names, one inode | **repaired**, inode unchanged, `nlink=2` preserved, both names see the fix. Defence held (a rename-into-place writer would have broken the link) |
| 8 | `f08-symlink-in` | `pkg/geom.py -> ../real/geom.py`, both in root | **repaired** at `real/geom.py`; the symlink is still a symlink. Defence held |
| 9 | `f09-symlink-out` | link out of root, **assertion-only** failure | **refused**, "candidate files tried: none found". Defence held — see §5 |
| 10 | `f09b` | same, forced with `fluidfix repair --file pkg/geom.py` | **refused**, "no observation named a kind this vocabulary can repair" — the packet showed *0 executed lines*. Defence held |
| 11 | `f10-future-mtime` | future-dated `.c` in a Python repo | **repaired** — the Python guard has no staleness probe. Not affected |
| 12 | `f11-mixed-eol` | CRLF file with one bare-LF line | **repaired**, 6 CR / 7 LF before and after. Defence held |
| 13 | `f12-latin1` | PEP 263 latin-1 source (legal Python) | **crash** — uncaught `UnicodeDecodeError`, exit 1 (S4, low). Tree byte-identical |
| 14 | `f13-symlink-out-tb` | link out of root, failure raises **inside** the source so the traceback carries its frame | **REPAIRED — attack landed (S2)** |
| 15 | `f14-crlf-span` | CRLF file, taught 2-line `SpanEdit` repair | **REPAIRED with corrupted line endings — attack landed (S2)** |
| 16 | `probe_stale.py` | `stale_binary()`, 6 inputs | **poisoned by one future mtime, and by a symlink out of root — attack landed (S4 + S3)** |
| 17 | `probe_recover.py` | `recover_inflight()` through a symlink | **writes outside the root — same escape as #14** |

## 4. Outcome

### S2-a — a repair written OUTSIDE the repo root, through a symlink

Reproduction:

```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/13-stale-and-symlink
./reproduce.sh f13
```

Layout: fluidfix is given `.../f13-symlink-out-tb/repo`. The only source is
`repo/pkg/geom.py`, a symlink to `../../outside/geom.py` — a sibling directory
the tool was never given. The bug raises `IndexError` inside `geom.py`, so the
traceback carries the frame `.../repo/pkg/geom.py:2` (the *link* path — Python's
loader does not resolve symlinks for `co_filename`; only pytest's own rootdir
handling and coverage.py do, which is why attempt #9 failed and this one does
not).

fluidfix's report:

```
[14:36:47] pkg/geom.py: repaired line 2 in 3 suite runs (2.5s):
  - return xs[2]
  + return xs[1]
=== guard exit: 0 ===
```

The diff fluidfix wrote — to `fixtures/f13-symlink-out-tb/outside/geom.py`,
which is **not under the root**:

```
2c2
<     return xs[2]
---
>     return xs[1]
```

`repo/pkg/geom.py` is still `lrwxr-xr-x ... -> ../../outside/geom.py`; the repo
fluidfix was pointed at contains no changed byte. The whole change landed in a
directory outside the declared blast radius, under a name the report never
mentions.

Two riders, both measured:

* `--dry-run` (`logs/f13-dryrun.log`) writes the mutation out of root as well,
  then restores it out of root, and emits `.fluidfix/proposed.patch` with the
  header `--- a/pkg/geom.py` — a path that in a real git repo is a *symlink
  blob*, so `git apply .fluidfix/proposed.patch` (the command it prints) cannot
  apply this hunk.
* `probe_recover.py` shows the same escape in the crash journal:
  `.fluidfix/inflight.json` records the relative name `pkg/geom.py`, and
  `recover_inflight()` writes the payload straight through the link into
  `outside/geom.py`. A journal left by a killed run therefore rewrites an
  out-of-tree file on a later, unrelated invocation.

**Severity: S2** — a file the user did not put in the repo is left in a state
they did not have, invisibly to the repo, to `git status`, and to the report.

**Classification: observation.** The law was never given a bit for this and
could not have been. `find_candidate_files` measured containment with
`os.path.normpath` where `os.path.realpath` is the only test that means
anything, and `_write` measured nothing at all — `open(path, "w")` follows the
link. The byte reaching `decide()` at ship time was `situation(BUILT=True)` =
`0x201`, and `decide(0x201) -> SHIP` is correct *for the repair it was told
about*. Nothing in the byte says which file was written. The missing
measurement is one line: `os.path.realpath(full).startswith(realpath(root))` at
guard.py:137, plus the same on the `--file`/journal paths.

### S2-b — a shipped repair corrupts a CRLF file's line endings

Reproduction:

```
./reproduce.sh f14
```

CRLF source, and a taught class (kind 4, `dict_span.py`) whose repair is a
two-line `SpanEdit` — the documented CHANGE_GRANULARITY shape for a fix neither
line can make alone.

```
[14:38:14] pkg/geom.py: repaired line 2 in 4 suite runs (1.6s):
  - t = a - b
    return -t
  + t = a + b
    return t
```

Bytes:

```
before  len 86  CRLF 7  bare-LF 0
  b'def add(a, b):\r\n    t = a - b\r\n    return -t\r\n\r\n\r\ndef scale(v, k):\r\n    return v * k\r\n'
after   len 84  CRLF 6  bare-LF 1
  b'def add(a, b):\r\n    t = a + b\n    return t\r\n\r\n\r\ndef scale(v, k):\r\n    return v * k\r\n'
```

A pure-CRLF file now has one bare LF at line 2. The report shows a two-line
repair and says nothing about endings; nothing the user is shown reveals it.
On a checkout with `* text eol=crlf`, or any CRLF-only toolchain, this is a
mixed-ending file and git will re-flag the hunk. The loss is exactly N-1 CRs
for an N-line span: loop.py:320 preserves `raw[e_-1]`'s ending and takes every
interior ending from `cand.text`, which the transform wrote LF-joined.

**Severity: S2** — corruption. The program is right; the file is not what the
user had, in a way the repair never proposed and the report never states. It
also directly contradicts the byte-exactness claim for the span path (relevant
to 15-byte-exact-audit).

**Classification: actuation.** The observation byte at ship time was
`situation(BUILT=True)` = `0x201`; `decide(0x201) -> SHIP`, and SHIP is right —
one green, unambiguous, uncapped candidate existed. The law ruled correctly on
a correct byte and the body then wrote bytes the adjudicated repair did not
contain: the taught transform proposed the *text* `"    t = a + b\n    return t"`
and the writer, not the transform, chose the interior line ending. (The
alternative reading — that candidate construction is upstream of the law and so
this is `observation` — is defensible; I call it actuation because the suite
adjudicated, and the law shipped, exactly the byte string that was written, so
nothing was mis-measured. What was wrong is the *rule for building* that string
from the file's own endings, which the single-line path at loop.py:281/329 gets
right and the span path does not.)

### S4 (+S3) — a UTF-8 BOM makes every candidate un-runnable, and the refusal says the suite rejected them

Reproduction:

```
./reproduce.sh f04
```

`pkg/geom.py` is the control file with a leading `EF BB BF`. CPython imports it
without complaint — the fixture's own suite runs (`1 failed, 1 passed`), which
is what makes this a defect fluidfix should repair. `.fluidfix/last_refusal.json`:

```json
"rejected_candidates": [
 {"at": "pkg/geom.py:3", "tried": "    return b - a",
  "why": "does not compile: invalid non-printable character U+FEFF (geom.py, line 1)"},
 {"at": "pkg/geom.py:3", "tried": "    return a + b",
  "why": "does not compile: invalid non-printable character U+FEFF (geom.py, line 1)"}
]
```

The second entry **is the correct repair** — byte-identical to the one f01
ships. It was discarded without a single suite run.

Two false claims ride on it (S3):

* `"does not compile"` — it compiles. Written to disk it is a valid module;
  only `compile()` **on a `str`** rejects U+FEFF, because
  `open(..., encoding="utf-8")` at loop.py:182 leaves the BOM in the text where
  `encoding="utf-8-sig"` would have removed it.
* the hint: *"every generated candidate was rejected by the suite (engine law:
  REFUTED -> HARVEST_COUNTEREXAMPLE)"*, and the summary *"fault is outside the
  taught vocabulary"*. The suite never ran on any candidate, and the fault is
  squarely inside the vocabulary.

**Severity: S4**, with an S3 rider on both the per-candidate `why` and the
run-level hint.

**Classification: observation** (`logs/probe_bytes.log`):

```
byte AS DELIVERED       situation(REFUTED=True)                  = 0x240  -> HARVEST_COUNTEREXAMPLE
byte AS IT SHOULD BE    situation(BUILT=True, AMB=0, CAPPED=0)   = 0x201  -> SHIP
```

The law ruled correctly on the byte it was handed. `REFUTED` was set from a
compile gate measuring the wrong artefact (a `str` that still carries the BOM,
rather than the file the interpreter will actually load), so `BUILT` was never
raised. Fix is a codec: `utf-8-sig` on read, or strip a leading `﻿` before
`compile()`.

### S4 (+S3) — `stale_binary()` is pinned True by any one future-dated file, and the advised remedy cannot clear it

Reproduction:

```
./reproduce.sh f15     # unit probe
```

`logs/probe_stale.log`:

```
A  binary newer than all sources                           -> False   (correct)
B  src/geom.c edited after the build (true positive)       -> True    (correct)
C  vendor/third_party.h mtime = +1 year, never compiled    -> True    (WRONG)
C2 ... after rebuilding the binary (the advised fix)       -> True    (WRONG, and now unfixable)
D  src/shared.h -> OUTSIDE the root, mtime = +1 year       -> True    (WRONG)
E  ... same symlink, sane mtime (control)                  -> False
```

End to end (`logs/f15-cguard-stale.log`), with a freshly built binary and the
only future-dated file being an uncompiled vendored header:

```
fluidfix: the test binary in build is older than your sources, so the suite that just ran is not the code on disk.
  Every verdict from here would be noise — a candidate cannot be judged against a binary that does not contain it.
  fix: rebuild from scratch (remove build and re-configure), then re-run.
```

Both sentences are false: the binary contains every source it compiles, and the
suite that ran *is* the code on disk. The remedy is worse than false — C2 shows
rebuilding does not change the verdict, because no achievable binary mtime can
exceed a timestamp a year in the future. The C guard is bricked on that repo
until a human finds the timestamp. This needs no adversary: a `cp -p`, a
tarball, a clock-skewed NFS or CI cache mount, or a vendored drop produces it.
Row D adds the symlink variant — the poisoning file need not even be in the
repo, because `os.walk` refuses to follow *directory* links but `getmtime`
happily follows *file* links.

**Severity: S4**, S3 rider on the reason and the remedy.

**Classification: observation.** The law is never consulted at all here — this
is a bare `raise CBuildError` inside `COracle.failing_output()`
(coracle.py:257), so there is no ruling to be wrong. The measurement is wrong
in three independent ways: it counts files the build never compiles, it follows
symlinks out of the tree, and it never sanity-checks the timestamp against
`time.time()`.

### S4 (low) — a read-only or non-UTF-8 source crashes instead of refusing

`f05-readonly` (mode 0444) dies with an uncaught `PermissionError` at
loop.py:75; `f12-latin1` (a legal PEP 263 latin-1 module) dies with an uncaught
`UnicodeDecodeError` at localize.py:101. Both print a raw Python traceback and
exit **1**, which `fluidfix guard --help` does not list ("0 green or repaired,
2 refused"), and neither writes `.fluidfix/last_refusal.json`, so a CI job
keyed on the refusal report sees nothing.

**Integrity held in both**: the file is byte-identical afterwards, mode intact,
and the journal is cleared (`_write` raises before `wrote = True`, so the
`finally` correctly declines to restore).

**Classification: actuation.** The design's output space is
`{repair, honest refusal}`; the body produced a third thing.

## 5. What defended

* **In-place `open(path, "w")` rather than write-to-temp-and-rename.** This is
  the single best decision in the writing path. It preserved mode 0755
  (`f06`), preserved the inode and `nlink=2` on a hardlinked source (`f07`),
  and preserved the symlink *as a symlink* (`f08`). A rename-into-place writer
  — the usual "atomic write" idiom — would have failed all three.
* **`newline=""` on both read and write, plus `src.split("\n")` and the
  `rstrip("\r")` / `ending` reattachment at loop.py:281+329.** This is a real,
  deliberate defence and it held completely for single-line repairs: pure CRLF
  (`f03`), mixed CRLF/LF (`f11`), and no trailing newline (`f02`) each came
  back with one byte changed and identical length. Only the `SpanEdit` branch
  fails to mirror it.
* **`_write(path, src)` from the in-memory original, in a `finally`.** Every
  refusal and every crash left the file byte-identical. I could not find a
  shape that stranded a mutation.
* **`wrote` is set *after* the write.** This is what stops the read-only crash
  from becoming a corruption: the `finally` does not attempt a restore it
  cannot perform.
* **pytest and coverage.py both resolve symlinks.** This is why attempt #9
  failed. With an assertion-only failure, coverage reports the *real* path, the
  lexical containment check correctly rejects it as out-of-root, and the guard
  refuses with "candidate files tried: none found". The escape (#14) needs the
  traceback to carry a frame from the file itself, i.e. an exception-shaped
  bug. The containment check is doing real work — it is just resting on someone
  else's `realpath()`.
* **`build_packet`'s coverage matching.** Forcing the out-of-root file with
  `repair --file` (attempt #10) still refused, because the packet matched 0
  executed lines for `pkg/geom.py` — a second, independent barrier.
* **`_is_test_path`, the harness cross-examination, and the compile gate** all
  behaved as documented; none of them was the thing that let anything through.

## 6. Verdict

fluidfix held on line endings, trailing newlines, permissions, hardlinks and
rollback integrity, and its single-line writer is genuinely byte-exact — but it
does not hold on **containment**: a symlink inside the root is written straight
through to a file outside it and reported under the in-root name (S2,
`observation`, guard.py:137 is lexical where it must be `realpath`, and
`recover_inflight` repeats the escape), and it does not hold on the
**`SpanEdit`** writer, which drops N-1 CRs from an N-line span in a CRLF file
and ships it as a clean repair (S2, `actuation`, loop.py:320).
