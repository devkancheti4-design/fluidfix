# fluidfix quickstart — guard your repo in 5 minutes

For beginners. No config files, no account, no API keys. Free (open source).
The only requirement: your project is Python and has at least one test that
runs with `pytest`.

## Step 1 — Install and check it

```bash
pip install fluidfix
fluidfix selfcheck
```

You should see `SELFCHECK PASS` at the end. That means the repair engine just
re-proved all of its own math on your machine. If it ever says FAIL, don't
use it (and please report it).

## Step 2 — Make sure you have a test

fluidfix never guesses — **your tests are the judge**. No tests, nothing to
guard. If your new repo has none yet, one tiny test is enough to start.
Example project:

```python
# billing.py
def price_after_tax(price, rate):
    return price * (1 + rate)
```

```python
# test_billing.py
from billing import price_after_tax

def test_tax():
    assert price_after_tax(100, 0.1) == 110.00000000000001
```

Check it runs: `pytest -q` → should say `1 passed`.

## Step 3 — Run the guard

```bash
fluidfix guard . --commit
```

You don't tell it which file is broken — it finds that itself. Three things
can happen, and all three are safe:

| Your repo | What fluidfix does |
|---|---|
| Tests are green | Touches **nothing**. Prints "suite green — nothing to do". |
| A mechanical bug (flipped `+`/`-`, off-by-one number, wrong `>=`…) | Finds the file, fixes the line, re-runs your tests, and commits `fluidfix: restore <file>:<line>` |
| Any other bug | **Refuses loudly**, leaves every file exactly as it was, exits with code 2. That bug is yours to fix — which is the right thing. |

Try it yourself: break `billing.py` by changing `(1 + rate)` to `(1 - rate)`,
commit that, then run the guard and watch `git log`.

## Step 4 — Let it keep watch

On your own machine (checks every 15 minutes):

```bash
fluidfix guard . --interval 900 --commit
```

Or on GitHub, so every push is checked — create
`.github/workflows/fluidfix.yml`:

```yaml
name: fluidfix
on: [push]
jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e . pytest fluidfix
      - run: fluidfix guard .
        # exit 0 = tests green (or auto-repairable)
        # exit 2 = a real bug fluidfix won't guess at — fix it yourself
```

## Good to know

- **It can't break your code.** Every candidate fix must pass your full test
  suite or it's rolled back byte-for-byte. A refused repair leaves the repo
  byte-identical.
- **If your project lives in a venv**, point the guard at it:
  `fluidfix guard . --python .venv/bin/python --commit`
- **Slow test suite?** Raise the budget: `--suite-timeout 900`.
- Want the full walkthrough with expected outputs (every step is verified by
  CI)? Read [DEMO.md](DEMO.md).

That's the whole setup. Questions or stuck? devkancheti4@gmail.com
