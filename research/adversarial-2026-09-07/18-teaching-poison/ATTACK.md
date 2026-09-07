# 18-teaching-poison — teaching fluidfix from a bad worked example

Agent 18 of 20, 2026-09-07. Everything below is in this directory; rerun with
`./reproduce.sh` (~90s, one run at a time, `nice -n 15` + a perl-alarm timeout
wrapper in `run.sh` — this machine has no coreutils `timeout`). No fluidfix
source, test, doc or git state was touched.

---

## 1. Target

`docs/TEACHING.md` / `acts.register()` / `load_dictionary()` — teach fluidfix a
fault class from a **wrong** worked example, and from an example that
generalises to a **dangerous** class, then run the poisoned guard against a
healthy repo and a repo with an unrelated defect.

## 2. Attack design

The teaching path moves the vocabulary from fluidfix's control into the user's.
Three properties looked attackable:

1. **Nothing validates a teacher.** `register()` is the whole contract. The
   docs describe good and bad appliers in prose, so the question is whether any
   of that prose is enforced.
2. **User kinds 4–7 sit numerically *ahead* of shipped kinds 8–12.** The
   mechanical observer emits kinds in ascending order (`observers.py:37`,
   `sorted(KINDS.items())`) and `EMIT` takes the lowest live bit
   (`lanes.py:21`). So `greens[0]` — the candidate `_rule` ships — is whichever
   the *lowest* kind produced. A taught class therefore deterministically
   outranks fluidfix's own correct shipped repair whenever both green. The docs
   present 4–7 as an isolated reservation ("no fluidfix release will claim
   them"); it is a reservation, not an isolation.
3. **`SpanEdit` anchor safety is a containment test, not a proximity test.**
   `docs/TEACHING.md` claims: *"Anchor safety: the span must contain the
   observed line (`start <= obs.lineno <= end`) and lie inside the file … **An
   observation may not edit code it never pointed at.***" The enforced check is
   `loop.py:312-313`:

   ```python
   if not (1 <= s_ <= e_ <= len(raw)) \
           or not (s_ <= obs.lineno <= e_):
       continue
   ```

   `SpanEdit(1, len(file), …)` satisfies both clauses. The blast radius is the
   whole file; the advertised property (an observation bounds what it may edit)
   is not the property enforced (the span merely has to swallow the
   observation). Everything outside the failing test's coverage is then
   unjudged, and the suite — the only judge — cannot see it.

Attack (2) with a wrong worked example; attack (3) with a dangerous class.

## 3. Attempts

### 3.1 What does `register()` refuse? (`probe_register.py`, `logs/probe_register.log`)

Ten deliberately bad teachers. Result: **the only validation in the teaching
path is `0 <= kind <= 15`.**

| teacher | result |
|---|---|
| applier contradicts its own `description` | ACCEPTED |
| `signal = re.compile("")` (matches every line) | ACCEPTED |
| `description` written as an instruction, not an observation (the doc's own "bad" example) | ACCEPTED |
| applier returns `None` (doc: "never `None`") | ACCEPTED |
| applier raises (doc: "never raise") | ACCEPTED |
| `signal` is a plain `str`, not a compiled regex | ACCEPTED |
| `applier` is not callable at all | ACCEPTED |
| `register(3, …)` clobbers a shipped class | ACCEPTED, **loud RuntimeWarning** |
| `register(16, …)` | **ValueError: kind must be 0..15** |
| second `register()` on a live kind | ACCEPTED, silent replace |

`load_dictionary` is `exec(compile(open(path).read()))` (`acts.py:352-363`) —
a dictionary is arbitrary code by design.

### 3.2 A2 — the wrong worked example, on the repo it was taught from (no finding)

`fixtures/repoA_incident` + `fixtures/poison_wrong.py` (incident INC-9001: the
on-call engineer saw one negative number and wrote the fix down as `abs(...)`).
Baseline refuses honestly ("fault is outside the taught vocabulary"); with the
dictionary it ships `return abs(balance - fee)`.

**Not a finding.** That suite asserts `net_change(5, 8) == 3`, so `abs()` is a
correct answer *to the spec as written*. Reported for completeness only.

### 3.3 A5 — first hijack attempt against a shipped class (failed)

`repoE_shipped_class`, defect `return used - paid`. The taught kind 4 lost:
shipped **kind 2** (`swapped-return-operands`) also matches any `return a OP b`
and 2 < 4, so `greens[0]` was the correct `return paid - used`. **A defence
held by accident of numbering** — for `return` lines the shipped low kinds get
there first.

### 3.4 A7 — the hijack, moved off a `return` line (**S1**)

Same defect expressed as an assignment, so kind 2's signal cannot match and the
only shipped class that can repair it is **kind 11**
(`reversed-minus-operands`) — numerically *behind* the taught kind 4.

### 3.5 A3/A12 — the dangerous class (**S1**)

`fixtures/poison_class.py` teaches `docs/TEACHING.md`'s own walkthrough incident
(INC-3105, split lost its separator) but returns `SpanEdit(1, len(file), …)`
"so the module gets tidied at the same time". The tidy-up flips an uncovered
module-level compliance flag.

### 3.6 Attempts that were stopped (details in §5)

- poisoned guard vs. a **healthy** repo, all five dictionaries;
- kind-3 collision to deny a shipped class;
- appliers that raise / return `None` (looking for S2 corruption);
- getting a far-away span shipped while a competing correct green exists.

## 4. Outcome

### S1a — a taught class outranks fluidfix's own correct repair

```bash
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/18-teaching-poison
rm -rf fixtures/repoF_preempt && cp -R fixtures_pristine/repoF_preempt fixtures/
./run.sh 180 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix \
    guard fixtures/repoF_preempt --dictionary fixtures/poison_wrong.py
```

Control (same repo, no `--dictionary`) — fluidfix gets it **right**:

```
orders.py: repaired line 2 in 3 suite runs:
  - amount = used - paid
  + amount = paid - used
```

With the taught class loaded — fluidfix reports "repaired" and the program is
now wrong:

```
dictionary fixtures/poison_wrong.py: 1 fault class(es) registered
orders.py: repaired line 2 in 4 suite runs (2.1s):
  - amount = used - paid
  + amount = abs(used - paid)
```

```diff
--- fixtures_pristine/repoF_preempt/orders.py
+++ fixtures/repoF_preempt/orders.py
@@
 def refund(paid, used):
-    amount = used - paid
+    amount = abs(used - paid)
     return amount
```

Wrongness, demonstrated (`refund(4, 10)` should be `-6`):

```
refund(10,4) = 6   | suite pins 6
refund(4,10) = 6   | CORRECT is -6
```

**Classification: `observation`.** (Not a `ruling` — the law did the right
thing with the byte it was handed.) From `probe_byte.py`
(`logs/probe_byte.log`), the search found **two different green programs at one
site**:

```
greens found : 2 -> ['    amount = abs(used - paid)', '    amount = paid - used']
acts tried   : [8, 9, 0]        # 8 = shipped kind 3, 9 = taught kind 4, 0 = shipped kind 11
```

They came from **different candidate sets**, so `set_amb` stays `False`
(`loop.py:400-404` only sets it for two greens *inside one set*), and
`sites = {2}`, so `len(sites) > 1` is `False`. The proxy at `loop.py:219` is
therefore:

- **observation byte passed:** `situation(BUILT=True, AMB=False, CAPPED=False)`
  = `513` = `0b10_00000001` (bits 8–9 are the constant DEBUG job) — low byte
  `0b00000001` = **BUILT**
- **act the law returned:** `SHIP` → `_write(path, greens[0])`, and `greens[0]`
  is the taught kind 4's `abs()` because 4 < 11 in EMIT order
- **what the law WOULD have ruled on the correct byte:** the situation actually
  measured is *two different programs both green*, i.e. `AMB=True` →
  `situation(BUILT=True, AMB=True)` = `515`, low byte `0b00000011` =
  **BUILT+AMB** → `decide` = **`ADD_STATE`** — refuse, and ask for one pinning
  test. That is exactly the right answer here: `abs(used - paid)` and
  `paid - used` are two different programs, and the suite cannot tell them
  apart.

This is attack surface C from the brief, but the teaching-path fact is new and
is what makes it exploitable rather than theoretical: **kinds 4–7 are emitted
before shipped kinds 8–12, so a user dictionary silently and deterministically
wins every one-site tie against the shipped vocabulary.** A repo that fluidfix
repairs correctly today gets a *different, wrong* repair after any teammate
commits a `rules.py` — with no mention of the collision anywhere in the report.

### S1b — a taught class edits code the observation never pointed at

```bash
rm -rf fixtures/repoC_unrelated && cp -R fixtures_pristine/repoC_unrelated fixtures/
./run.sh 180 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix \
    guard fixtures/repoC_unrelated --dictionary fixtures/poison_class.py
```

```
dictionary fixtures/poison_class.py: 1 fault class(es) registered
ledger.py: repaired line 1 in 3 suite runs (2.1s):
```

```diff
--- fixtures_pristine/repoC_unrelated/ledger.py
+++ fixtures/repoC_unrelated/ledger.py
@@ -3 +3 @@
-AUDIT_ENABLED = True
+AUDIT_ENABLED = False
@@ -16 +16 @@
-    fields = row.split()
+    fields = row.split(",")
```

The observation was at **line 16**. The defect was at line 16. `AUDIT_ENABLED`
is at line 3 — 13 lines away, in a function (`record_audit`) the failing test
never executes and no test covers. `SpanEdit(1, 17)` satisfies both clauses of
the anchor check, so it was never skipped. The suite is green afterwards and
fluidfix reports success.

**Severity S1** (a change written to disk, "repaired" reported, compliance
logging silently off). **Classification: `observation`** — the loop never
measures the blast radius, so no bit describing it can reach the law; the byte
passed was `513` (`BUILT`) and `SHIP` was the correct act for that byte. There
is no bit in `BITS` for "this candidate edited lines the observation did not
point at", so the law was not given the chance to rule.

Persistence (question asked in the brief): **yes, for free, in any repo.** The
same dictionary, a different repo, zero new examples
(`fixtures/repoD_generalise`):

```
shipping.py: repaired line 1 in 3 suite runs (1.4s)
-AUDIT_ENABLED = True
+AUDIT_ENABLED = False
```

`docs/TEACHING.md` tells the user to commit the dictionary "so CI and every
teammate's guard share the same taught classes" — which is exactly the
distribution mechanism this needs.

### S3 — the report names a line that is neither the defect nor the observation

In S1b, `RepairResult.lineno` is set to the **span start** (`loop.py:322`,
`crepr, at = cand.text, s_`), so the guard prints `repaired line 1` and
`commit_repair` (`guard.py:684`) writes the commit subject
`fluidfix: restore ledger.py:1`. The observation was line 16 and the defect was
line 16. Nothing in the report says how many lines were rewritten or that any
of them lie outside the observed line. The word "restore" is also wrong for
this change — nothing was restored; `AUDIT_ENABLED` was flipped.

**Severity S3, classification: `wording`** — the outcome (whatever one thinks
of it) was described with the wrong line number and without its blast radius.

### S3/doc — a stated safety property that is not the property enforced

`docs/TEACHING.md`: *"An observation may not edit code it never pointed at."*
Falsified by S1b. The code enforces containment (`s_ <= obs.lineno <= e_`), not
proximity. **Classification: `wording`.**

## 5. What defended

These are real defences and they held cleanly.

1. **The green-suite precondition.** `loop.py:176-179`. Against a **healthy**
   repo all five poisoned dictionaries did nothing at all:
   `suite green — nothing to do`, and `diff -r` confirmed
   `fixtures/repoB_healthy` byte-identical each time. A poisoned vocabulary
   cannot start a search without a failing test, so it cannot corrupt a working
   repo.
2. **`register(kind=0..3)` warns loudly and the warning reaches the CLI.**
   The kind-3 collision printed, on stderr, with the offending file and line:
   ```
   fixtures/poison_kill.py:8: RuntimeWarning: register(kind=3) CLOBBERS the shipped
   fault class 'flipped-additive' — that class can no longer be observed or
   repaired; user dictionaries belong in kinds 4..7
   ```
   The shipped kind-3 defect in `repoG_additive` (repaired correctly at
   baseline) was then **refused**, tree byte-identical. That is a denial, but
   with a correct, loud, pre-announced reason — per the brief, **not** a
   finding. (Minor: the following line still reads `0 fault class(es)
   registered`, which counts *new* kinds; documented in the troubleshooting
   table, and the warning above it carries the real news.)
3. **Shipped low kinds get first refusal on `return` lines.** §3.3: kind 2's
   signal covers any `return a OP b`, so on return statements the taught class
   at kind 4 cannot pre-empt. The S1a hijack only works on lines the shipped
   kinds 0–3 cannot reach.
4. **Coverage localisation bounds the poison's reach.** Signals are matched
   only over the lines the failing test executed (`observers.py:31-42`), so a
   promiscuous signal cannot fire on code the failing test never ran. This is
   why an unrelated defect elsewhere in a file is not automatically hijackable.
5. **A crashing or `None`-returning applier aborts the pass without corrupting
   the tree.** Both `poison_crash.py` and `poison_none.py` ended in a traceback
   that names the dictionary file and line; `diff` confirmed `calc.py`
   byte-identical afterwards. Exactly as `docs/TEACHING.md` documents. **No S2
   found anywhere in this target.**
6. **`kind > 15` is refused** — `ValueError: kind must be 0..15`.

## 6. Verdict

**fluidfix held against a healthy repo and against every corruption attempt,
but did not hold on the teaching path itself: nothing whatsoever validates a
teacher, a taught class at kinds 4–7 silently outranks fluidfix's own correct
shipped repair at kinds 8–12 whenever both green at one site (S1a), and
`SpanEdit`'s anchor check permits a whole-file candidate, so a taught class
edits code the observation never pointed at while the report names the wrong
line (S1b + S3).**
