# fluidfix quickstart — guard your repo in 5 minutes

For beginners. No config files, no account, no API keys. Free (open source).
The only requirement: your project is Python and has at least one test that
runs with `pytest`.

## Step 1 — Install and check it

```bash
pip install fluidfix pytest-cov
fluidfix selfcheck
```

(`pytest-cov` is how fluidfix finds the broken *file* in a big repo when a traceback doesn't name it — always install it alongside.)

You should see `SELFCHECK PASS` at the end. That means the repair engine just
re-proved all of its own math on your machine. If it ever says FAIL, don't
use it (and please report it).

## Step 2 — Make sure you have a test

fluidfix never guesses — **your tests are the judge**. No tests, nothing to
guard. If your new repo has none yet, one tiny test is enough to start.

### Never written a test? Here's the whole idea in 2 minutes

A test is just a tiny file that **calls your function and checks the
answer**. Three rules and one formula:

1. Put it in a file whose name starts with `test_` (e.g. `test_billing.py`).
2. Inside, write a function whose name starts with `test_`.
3. In it, one line: `assert your_function(example_input) == expected_answer`.

```python
# test_anything.py — the universal pattern
from mymodule import my_function

def test_my_function():
    assert my_function(2, 3) == 5      # call it, check the answer
```

**Don't know what the expected answer should be?** Use the paste trick: your
code works today, so run it once and freeze that answer.

```bash
python -c "from billing import price_after_tax; print(price_after_tax(100, 0.1))"
# it prints: 110.00000000000001  ← copy this
```

…then paste it into the assert:
`assert price_after_tax(100, 0.1) == 110.00000000000001`. That's called a
regression test — it says "whatever this did today, keep doing it" — and
defending exactly that is fluidfix's whole job.

One test per function you care about is plenty to start. Run them all with
`pytest -q`.

### The example project used below:

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
      - run: pip install -e . pytest pytest-cov fluidfix
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
