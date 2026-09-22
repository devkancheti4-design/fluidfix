#!/bin/zsh
# Rebuilds the demo repo to the exact state the recording starts from: a green project with ONE
# regression commit on top. Nothing is pre-repaired; every fluidfix run in the video happens live.
set -e
ROOT="$1"; HERE="${0:A:h}"; rm -rf "$ROOT"; mkdir -p "$ROOT/ledgerly" "$ROOT/tests"; cd "$ROOT"
: > ledgerly/__init__.py
cat > ledgerly/ledger.py <<'PY'
class Ledger:
    def __init__(self, entries):
        self.entries = list(entries)

    def first(self):
        return self.entries[0]

    def last(self):
        return self.entries[-1]

    def size(self):
        return len(self.entries)

    def total(self):
        return sum(self.entries)
PY
cat > ledgerly/balance.py <<'PY'
def closing_balance(ledger):
    return ledger.last()


def average(ledger):
    return ledger.total() / ledger.size()


def statement(ledger):
    return f"{ledger.size()} entries, last {ledger.last()}, total {ledger.total()}"
PY
cat > ledgerly/report.py <<'PY'
def headline(ledger):
    return f"closing {ledger.last()} over {ledger.size()} entries"


def footer(ledger):
    return f"{ledger.size()} entries"
PY
cat > ledgerly/invoice.py <<'PY'
VAT = 0.19


def gross(net):
    return round(net * (1 + VAT), 2)
PY
cat > ledgerly/text.py <<'PY'
def cut_at(text, k):
    """Index k shares of the way to the text's LAST position."""
    return int(k * (len(text) - 1))
PY
cat > tests/test_ledger.py <<'PY'
from ledgerly.ledger import Ledger


def test_total():
    assert Ledger([1, 2, 3]).total() == 6


def test_last_and_size():
    l = Ledger([5, 1, 2, 7])
    assert l.last() == 7 and l.size() == 4
PY
cat > tests/test_balance.py <<'PY'
from ledgerly.ledger import Ledger
from ledgerly.balance import closing_balance, average, statement


def test_closing():
    assert closing_balance(Ledger([5, 1, 2, 7])) == 7


def test_average():
    assert average(Ledger([2, 4])) == 3


def test_statement():
    assert statement(Ledger([5, 1, 2, 7])) == "4 entries, last 7, total 15"
PY
cat > tests/test_report.py <<'PY'
from ledgerly.ledger import Ledger
from ledgerly.report import headline, footer


def test_headline():
    assert headline(Ledger([5, 1, 2, 7])) == "closing 7 over 4 entries"


def test_footer():
    assert footer(Ledger([5, 1, 2, 7])) == "4 entries"
PY
cat > tests/test_invoice.py <<'PY'
from ledgerly.invoice import gross


def test_gross():
    assert gross(100) == 119.0
PY
cat > tests/test_text.py <<'PY'
from ledgerly.text import cut_at


def test_cut_at_full():
    # the only case this suite ever asks: k = 1
    assert cut_at("abcdef", 1) == 5
PY
cat > pyproject.toml <<'PY'
[project]
name = "ledgerly"
version = "1.4.0"

[tool.pytest.ini_options]
pythonpath = ["."]
PY
printf '__pycache__/\n.pytest_cache/\n.fluidfix/\nrules*.py\n' > .gitignore
cp "$HERE/rules.py" "$HERE/rules_naive.py" .
git init -q -b main
git add -A
git commit -qm "ledgerly: ledger, balances, reports, invoices, text"
sed -i '' 's/net \* (1 + VAT)/net * (1 - VAT)/' ledgerly/invoice.py
git commit -qam "invoice: tidy the vat formula"
echo "demo repo ready at $ROOT"; git log --oneline
