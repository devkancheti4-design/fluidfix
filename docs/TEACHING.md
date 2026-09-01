# fluidfix — teaching new fault classes (tested)

The four shipped acts are a starter dictionary, not a ceiling. When the guard
refuses, that refusal is a machine-readable teach-me signal: write the
incident down once as a `register()` call, and every future member of that
fault class is repaired for free — decided by the kernel at zero tokens,
judged by your own suite. This document is the complete teaching contract:
the `register()` signature, the `Observation` your transform receives, a
30-minute walkthrough from refusal to taught class, candidate sets, and
`SpanEdit`.

The walkthrough's dictionary below is extracted verbatim and executed by
`tests/test_teaching.py` on every CI run, as is the fuller three-class
dictionary in [`examples/company_rules.py`](../examples/company_rules.py) —
if this document drifts from reality, the build goes red.

```
guard refuses (exit 2) ──► .fluidfix/last_refusal.json      the teach-me signal
                       ──► write the incident down ONCE     register() in a dictionary file
                       ──► guard . --dictionary rules.py    the class repairs itself,
                                                            forever, at zero tokens
```

---

## The register() contract

```python
register(kind, name, description, signal, applier) -> int   # the act code
```

One call teaches one fault class. The router is never edited: it infers the
new class's act code from the same single worked example it always uses, so
teaching costs exactly one registration, once. The returned act code is
informational — you never store or reference it.

### `kind` — the class number

| kinds | owner |
|---|---|
| 0–3 | shipped vocabulary (strictness, literal-off-by-one, swapped-return-operands, flipped-additive) |
| **4–7** | **yours — reserved for user dictionaries; no fluidfix release will claim them** |
| 8–15 | reserved for future shipped classes — don't squat here |

- Hard bounds 0–15 (`ValueError` outside): the kernel routes mod 16, so one
  dictionary holds 16 classes.
- Registering an occupied kind **replaces** it. That is how you would
  deliberately override a shipped class — and how two dictionary files
  collide accidentally. Keep user classes in 4–7, one kind per class.
- Renumbering your own kinds is always safe: act codes are re-derived from
  the worked example on every call, never stored.

### `name` — a short slug

Appears in reports and logs (`kind 4 -> act 9`, refusal JSON). Keep it a
hyphenated noun phrase: `missing-get-default`, `wrong-attribute`.

### `description` — the observation sentence

This sentence **is** the LLM observer contract: `ClaudeObserver` receives it
verbatim in its prompt, as `<kind> = <name>: <description>`. Write what an
observer must *see* on the defective line — an observable fact, never an
instruction or a fix:

- good: `'a .get(key) with no default, letting None poison arithmetic'`
- bad: `'add a default of 0 to .get calls'` (a fix — observers never fix)
- bad: `'the invoice bug from March'` (nothing observable on the line)

The mechanical observer never reads it (it uses `signal`), so under
`--observer mechanical` the sentence is documentation — write it anyway; it
is what makes the dictionary portable to `--observer claude`.

### `signal` — the line-signal regex

A compiled regex. The mechanical observer reports this kind for a line iff
`signal.search(line)` matches — checked only over the *localised* lines the
failing test executed, never the whole file. Two consequences:

- The signal answers "can this line exhibit the class?", not "is this line
  broken?" — false positives cost suite runs, not correctness (the suite
  rejects them).
- An over-broad signal is a grind: every matching localised line spawns a
  candidate set, and every candidate is a full suite run. Anchor it on the
  class's concrete tokens (`\.get\(`, `round\(`), not on `.` or `\w`.

Lines are matched with their endings stripped (no `\n`/`\r`).

### `applier` — the transform

```python
applier(line: str, obs: Observation) -> str | list[str | SpanEdit]
```

Called with the defective line (no line ending) and the observation. Three
return shapes:

| return | meaning |
|---|---|
| `str` | one candidate — the fix is a pure rule over the line |
| `list[str]` | a candidate **set**, tried in order, capped at 32 — for values mined from the repo (see below) |
| `list` containing `SpanEdit` | atomic multi-line candidates (see below); a `SpanEdit` must be returned *inside* the list, never bare |

Rules, all enforced by how the loop works:

- **Keep the transform total.** When the class does not apply to the line,
  return the line unchanged (or `[line]`) — that is NOPROGRESS and the loop
  moves on. Never return `None`, never raise: an applier exception aborts
  the whole pass with a traceback (the tree is still restored byte-exactly).
- A candidate identical to the current line is skipped; duplicates across
  the set (and across kinds) are tried once.
- A candidate string may contain `\n`: one taught example can rewrite the
  defective line into a whole corrected block (CI-tested: mean-to-median,
  5 lines from 1). Prefer `SpanEdit` when *existing* lines below must also
  change — a block ending in `return` can strand them as dead code.
- **The suite stays the judge.** Candidates that don't green the suite are
  rolled back byte-exactly; none passing means refusal; two *different*
  passing candidates refuse as AMBIGUOUS with a pinning-test ask. A wrong
  transform cannot land — precision is bounded by suite strength.

### Scope inside a dictionary file

A dictionary is a plain Python file whose top level calls `register()`.
`register`, `re`, and `SpanEdit` are pre-bound; ordinary imports work
(`import ast` at the top is fine, as are `def` helpers). Load it with
`--dictionary rules.py` (both `fluidfix guard` and `fluidfix repair`) or
from Python:

```python
from fluidfix.acts import load_dictionary
load_dictionary("company_rules.py")     # -> number of NEW kinds registered
```

Version the file next to the code it maintains and commit it, so CI and
every teammate's guard share the same taught classes.

## The Observation your transform receives

| field | contents |
|---|---|
| `lineno` | 1-based line number of the observed line in the defect file |
| `kinds` | fault kinds reported for the line, most specific first (`[]` = refuse) |
| `literal_value`, `literal_occurrence` | kind-1 pointer: the wrong literal's digits and which occurrence on the line, 1-based |
| `op_occurrence` | kind-3 pointer: which binary ` + `/` - `, left to right, 1-based |
| `note` | free text, empty by default |
| `file` | defect file, relative to root — **repo context** |
| `root` | project root, absolute — **repo context** |
| `all_lines` | full defect-file lines, endings stripped — **repo context** |

The three repo-context fields are populated by the repair loop just before
appliers run, so a taught transform can search the repo for values that live
off the broken line:

```python
def fix(line, obs):
    here = obs.all_lines[obs.lineno - 1]     # == line (endings stripped)
    below = obs.all_lines[obs.lineno]        # the next line, if any
    ...
```

When unit-testing a transform directly, set them yourself:
`Observation(lineno=2, all_lines=[...])`.

## What is teachable — the honest boundary

A class is teachable the moment its repair is **derivable from the line plus
what the repo already contains**:

- a pure rule over the line (flip, decrement, add-default) — return one
  candidate;
- a value that lives elsewhere in the repo (the right attribute name, a
  constant sibling code uses) — return a candidate list mined from
  `obs.all_lines` / `obs.root`;
- several lines wrong together — return a `SpanEdit`.

Fixes needing information that exists nowhere in the repo — a new algorithm,
an outside fact — are not transforms. Leave those refused; the refusal is
the feature that makes the repairs trustworthy.

---

## The 30-minute walkthrough: from refusal to taught class

The running incident: `inventory.py` parses comma-separated rows, and a
cleanup changed `row.split(",")` to `row.split()`. The suite is red; the
shipped vocabulary has no such class.

### 0:00 — read the refusal

```bash
fluidfix guard . --commit
```

```
REFUSED: fault is outside the taught vocabulary (candidate files tried:
inventory.py). Teach the class once — register() an observation + transform —
and its whole family becomes free.
```

Exit code 2, tree byte-identical, and a machine-readable signal in
`.fluidfix/last_refusal.json`:

```json
{
 "status": "refused",
 "candidates": ["inventory.py"],
 "hint": "...",
 "rejected_candidates": [ {"at": "inventory.py:2", "tried": "...", "why": "FAILED test_inventory.py::test_rows ..."} ]
}
```

`rejected_candidates` lists everything the shipped classes tried, each with
the exact failing test that killed it — read it to confirm the fault really
is a novel class and to see which line the loop was already pointing at.

### 0:05 — write the incident down as a worked example

Two lines, before and after:

```
fields = row.split()          <- whitespace-split shipped over comma data
fields = row.split(",")       <- the fix
```

Then pick the candidate shape: the fix is a pure rule over the line (no
repo search, no second line), so one string candidate. Pick the lowest free
user kind — 4.

### 0:10 — the dictionary file

```python
# company_rules.py — version this file next to the code it maintains
# Taught from ONE worked example (incident INC-3105):
#   fields = row.split()         <- whitespace-split shipped over comma data
#   fields = row.split(",")      <- the fix
register(
    4,                                   # kind: 4-7 are reserved for you
    "split-lost-separator",              # name, used in reports
    'a .split() with no separator applied to comma-separated text',
                                         # the observation sentence — LLM
                                         # observers receive it verbatim
    re.compile(r"\.split\(\)"),          # signal: when a line can exhibit it
    lambda line, o: line.replace(".split()", '.split(",")'),
)
```

### 0:15 — check it loads, then check the transform

```bash
python -c "from fluidfix.acts import load_dictionary; print(load_dictionary('company_rules.py'))"
# 1
```

And exercise the transform without running any suite:

```python
from fluidfix import Observation
from fluidfix.acts import load_dictionary, act_for, candidates
load_dictionary("company_rules.py")
assert candidates("    fields = row.split()", act_for(4), Observation(lineno=1)) \
    == ['    fields = row.split(",")']
```

### 0:20 — run the guard with the dictionary

```bash
fluidfix guard . --commit --dictionary company_rules.py
```

Expected output shape:

```
dictionary company_rules.py: 1 fault class(es) registered
[..] inventory.py: repaired line 2 in 2 suite runs (0.6s):
  - fields = row.split()
  + fields = row.split(",")
  committed
```

### 0:25 — the class is free, forever

Break a *different* file the same way and run the same command — it repairs
that too, zero new examples. Commit `company_rules.py`, then put the
`--dictionary` flag wherever the guard already runs:

```bash
fluidfix guard . --interval 900 --commit --dictionary company_rules.py   # cron/systemd
fluidfix guard . --dictionary company_rules.py                           # CI gate
```

Done. From here on this class costs four integer instructions per decision
and zero tokens.

---

## Candidate sets: when the right value lives in the repo

A pure rule can't fix `return u.name` when the correct attribute is `.id` —
the answer is not on the line. But it *is* in the repo. Return a candidate
**list** enumerated from the repo context; the suite tries each in order and
still refuses when none passes (from `examples/company_rules.py`, kind 5):

```python
import ast

def _attrs_in_repo(o):
    """Every attribute name used anywhere in the defect file."""
    try:
        tree = ast.parse("\n".join(o.all_lines or []))
    except SyntaxError:
        return []
    return sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})

register(
    5, "wrong-attribute",
    "a returned attribute that is the wrong one; the right name exists "
    "elsewhere in this file",
    re.compile(r"return \w+\.\w+"),
    lambda line, o: [re.sub(r"(return \w+)\.\w+", rf"\1.{a}", line)
                     for a in _attrs_in_repo(o)],
)
```

- Sets are capped at 32 candidates — enumerate tightly, don't flood.
- Every candidate is a full suite run: order the list best-guess-first when
  you can.
- The no-wrong-repairs contract is unchanged: none green means refusal, two
  different greens refuse as AMBIGUOUS.

## SpanEdit: several lines wrong together

When neither line's change alone can green the suite, single-line candidates
cannot land — the guard refuses (that boundary is itself CI-pinned). A
taught transform may instead return `SpanEdit(start, end, text)`: one
candidate replacing lines `start..end` (1-based, inclusive) **atomically**.

```python
SpanEdit(start, end, text)   # text: full replacement block, no trailing
                             # newline; may contain "\n"
```

The contract, all carried over from single-line candidates:

- **Anchor safety**: the span must contain the observed line
  (`start <= obs.lineno <= end`) and lie inside the file — a violating span
  is skipped without a write. An observation may not edit code it never
  pointed at.
- Suite-adjudicated candidate by candidate; rejection rolls back
  byte-exactly (CRLF included); two *different* green spans refuse as
  AMBIGUOUS.
- Return it inside the candidate list, optionally alongside other
  candidates.
- Prefer a span over a block-candidate ending in `return`: the block leaves
  the old lines below as dead code no suite can see; the span deletes them.

From `examples/company_rules.py`, kind 6 — a rounding moved ahead of the
following accumulation, two lines that must swap roles together:

```python
# Taught from ONE worked example (incident INC-2358):
#   total = round(subtotal)          <- rounds too early
#   total = total + surcharge
# the fix, one atomic SpanEdit:
#   total = subtotal + surcharge
#   total = round(total)
def _round_last(line, o):
    m = re.match(r"^(\s*)(\w+) = round\((\w+)\)$", line)
    if not m:
        return [line]                       # not this class: no progress
    ind, acc, raw = m.groups()
    lines = o.all_lines or []
    nxt = lines[o.lineno] if o.lineno < len(lines) else ""
    m2 = re.match(rf"^\s*{acc} = {acc} \+ (\w+)$", nxt)
    if not m2:
        return [line]
    return [SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}{acc} = {raw} + {m2.group(1)}\n"
                     f"{ind}{acc} = round({acc})")]

register(
    6, "round-before-accumulate",
    "a round() applied before a following line adds to the rounded value; "
    "the two lines must swap roles together",
    re.compile(r"\w+ = round\(\w+\)"),
    _round_last,
)
```

## Testing a dictionary like code

A dictionary is code your repairs depend on — pin it. Registrations are
process-global, so save and restore the registries around each test (the
pattern every fluidfix test uses; `tests/test_teaching.py` is a living
example):

```python
import sys
from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once
from fluidfix.acts import load_dictionary

def test_split_class_repairs(tmp_path):
    (tmp_path / "mod.py").write_text(
        "def parse_row(row):\n    fields = row.split()\n    return fields\n")
    (tmp_path / "test_mod.py").write_text(
        'from mod import parse_row\n\ndef test_r():\n'
        '    assert parse_row("widget,4") == ["widget", "4"]\n')
    saved = dict(KINDS), dict(ACTS)
    try:
        assert load_dictionary("company_rules.py") == 1
        report = guard_once(Oracle(str(tmp_path), python=sys.executable),
                            MechanicalObserver())
        assert report.status == "repaired"
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
```

---

## Troubleshooting (each entry is a mechanical cause, not a guess)

| Symptom | Cause / fix |
|---|---|
| Refusal: "no observation named a kind this vocabulary can repair" | the signal never matched the defective line — check `signal.search(broken_line)` by hand; or the line never made it into the packet (install pytest-cov in the *target* interpreter so coverage localisation works) |
| Refusal: "every candidate left the suite red" | the transform's candidates are wrong, or the observation pointed at a different line — `.fluidfix/last_refusal.json` lists every rejected candidate with the exact test that killed it |
| `dictionary rules.py: 0 fault class(es) registered` | the count is *new* kinds only — the same process already loaded these kinds (a second `load_dictionary`, or another dictionary claimed the kind first); the transforms were still updated |
| `ValueError: kind must be 0..15` | the kernel routes mod 16 — renumber into 4–7 |
| A shipped class stopped repairing after loading a dictionary | your `register()` reused kind 0–3 and replaced the shipped class — move to 4–7 |
| The guard grinds (or `--budget` expires) after teaching | the signal is promiscuous: every matching localised line × every candidate × one full suite run — tighten the regex, shrink the candidate set, and use `--budget` so expiry stays an honest refusal |
| Refusal: AMBIGUOUS, "add one pinning test" | working as designed — two different candidates both green your suite, so the suite cannot pick; add the test that distinguishes them, never weaken the transform to guess |
| `ClaudeObserver` never reports your kind | the observation sentence is that observer's *entire* contract — rewrite it as an observable line-level fact (and keep kinds 0–15; the response schema rejects others) |
| Span candidates silently skipped | bounds or anchor safety: the span must lie inside the file and contain `obs.lineno` |
| The guard crashes with a traceback into your transform | keep appliers total — return the line unchanged (or `[line]`) when the class doesn't apply, never `None`, never raise (the tree is restored, but the pass is aborted) |
| A bare `SpanEdit` return crashes | return shape is `str` or `list` — wrap the `SpanEdit` in a list |

Full pipeline walkthrough with expected outputs: [DEMO.md](DEMO.md). The
complete runnable dictionary shown above:
[`examples/company_rules.py`](../examples/company_rules.py).
