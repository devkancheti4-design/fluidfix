# fluidfix — step-by-step demo (tested)

Every step below is executed by `tests/test_demo_walkthrough.py` on every CI
run — if this document drifts from reality, the build goes red. Expected
outputs are from real runs. The demo video in `docs/media/demo.mp4` follows
this exact script.

**Prerequisites:** Python ≥ 3.10, `git`, and the target project's own test
suite runnable with `pytest`. fluidfix's core has zero dependencies.

---

## Step 1 — Install and verify

```bash
pip install fluidfix
fluidfix selfcheck
```

Expected: `SELFCHECK PASS` after the exhaustive re-derivation — 4096 routing
cases, identity, composition, 256 dispatch states, termination. This runs
offline in about a second; if it ever fails, do not use the build.

## Step 2 — A service with a suite

Any project where `pytest` runs is a target. The demo service:

```python
# billing.py
def price_after_tax(p, rate):
    return p * (1 + rate)
```

```python
# test_billing.py
from billing import price_after_tax

def test_tax():
    assert price_after_tax(100, 0.1) == 110.00000000000001
```

`pytest -q` is green. Commit and deploy. fluidfix touches nothing while the
suite is green — that is a tested guarantee, not a habit.

## Step 3 — A regression ships; the guard repairs it

Someone flips the operator (`1 + rate` → `1 - rate`) and ships it. Run the
guard — note you do **not** tell it which file broke:

```bash
fluidfix guard . --commit
```

Expected output shape:

```
[..] billing.py: repaired line 2 in 4 suite runs (0.7s):
  - return p * (1 - rate)
  + return p * (1 + rate)
  committed
```

What happened: the guard found the fault file mechanically (traceback frames,
else failing-test coverage ranking), the kernel routed the observed fault kind
to its repair, your suite accepted the candidate, and the restoration was
committed as `fluidfix: restore billing.py:2`. Zero model tokens.

Deployment modes:

```bash
fluidfix guard .                  # one-shot: exit 0 green/repaired, exit 2 refused (CI gate)
fluidfix guard . --interval 900   # watch mode, every 15 minutes (cron/systemd)
```

## Step 4 — A novel bug class is refused, loudly

Ship a different defect — say `inv.get("tax")` losing its `, 0` default so
`None` poisons a sum. The shipped vocabulary has no such class:

```bash
fluidfix guard . --commit
```

Expected: `REFUSED: fault is outside the taught vocabulary ...`, exit code 2,
the working tree byte-identical, and a machine-readable teach-me signal in
`.fluidfix/last_refusal.json`. fluidfix never guesses: the refusal is the
feature that makes the repairs trustworthy.

## Step 5 — Teach the class from ONE example

Write the incident down once, as a fault-class dictionary. This is the whole
"how to give examples" contract — three parts per class:

```python
# company_rules.py — version this file next to the code it maintains
# Taught from ONE worked example (incident INC-2041):
#   due += inv["amount"] + inv.get("tax")      <- summed None, crashed
#   due += inv["amount"] + inv.get("tax", 0)   <- the fix
register(
    4,                                  # kind: 0-15, one per class
    "missing-get-default",              # name
    'a .get(key) with no default, letting None poison arithmetic',  # what an
                                        # observer must see (LLM observers get
                                        # this sentence verbatim)
    re.compile(r"\.get\((\"[^\"]+\"|'[^']+')\)"),        # signal: when a line
                                        # can exhibit the class
    lambda line, o: re.sub(r"\.get\((\"[^\"]+\"|'[^']+')\)",
                           r".get(\1, 0)", line),        # the repair transform
)
```

Rules of thumb (all enforced by how the pipeline works):

- **One class = one `register()` call.** The kind number is yours; the act
  code is inferred by the router from its single worked example — you never
  touch the kernel, and renumbering your classes never breaks anything.
- **The transform must be derivable from the defective line alone.** If the
  fix needs information the line doesn't carry (a wrong variable name, a
  missing guard), it is not a class fluidfix should own — leave it refused.
- **The suite stays the judge.** A wrong transform cannot land: candidates
  that don't green the suite are rolled back byte-exactly.
- `re` and `register` are in scope inside a dictionary file; nothing else is
  needed.

## Step 6 — The class is free, forever

```bash
fluidfix guard . --commit --dictionary company_rules.py
```

Expected: `dictionary company_rules.py: 1 fault class(es) registered`, then
the repair and the commit. Now break a *different* file with a *different*
key (`.get("ms")` in `metrics.py`) and run the same command — it repairs that
too. One example bought the class; every member is decided in four integer
instructions at zero tokens. Commit `company_rules.py` to the repo so CI and
every teammate's guard share the same taught classes.

## Step 7 — Same thing from Python

```python
import sys
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.acts import load_dictionary

load_dictionary("company_rules.py")
report = guard_once(Oracle(".", python=sys.executable), MechanicalObserver())
print(report.summary())        # repaired / green / refused — never a guess
```

`Oracle(python=...)` should point at the **target project's** interpreter
(its venv) so its test dependencies resolve.

---

## Troubleshooting (each entry is a measured failure mode)

| Symptom | Cause / fix |
|---|---|
| Repairs scored as failures | stale bytecode — fluidfix already runs `-B` and clears `__pycache__`; do the same in any wrapper you build |
| A whole library scores zero | a pytest plugin collides with a suite fixture (seen: `pytest-benchmark`) — fluidfix passes `-p no:benchmark` |
| Coverage localisation finds nothing | never run pytest-cov with `-x` (exit-first silently skips the JSON report — upstream bug, fluidfix avoids it) |
| Guard refuses on a suite slower than 300s | raise `--suite-timeout` / `--candidate-timeout` |
| Wrong interpreter / missing deps | pass `--python path/to/project/venv/bin/python` |
