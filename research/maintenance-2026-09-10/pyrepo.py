#!/usr/bin/env python3
"""Build `ledgerkit` — a small but genuine Python library with a real pytest
suite — at the given path, and commit it green as the base state.

Six modules, every boundary pinned by a test with a concrete value, so that for
each regression in catalog.py exactly one one-edit program is green.
usage: pyrepo.py <target-dir>
"""
import os, subprocess, sys, textwrap

FILES = {
"pyproject.toml": """\
[project]
name = "ledgerkit"
version = "1.4.2"

[tool.pytest.ini_options]
pythonpath = ["."]
""",
".gitignore": "__pycache__/\n.pytest_cache/\n.fluidfix/\n",
"ledgerkit/__init__.py": "",
"ledgerkit/money.py": '''\
"""Money arithmetic: cents-exact rounding, allocation, clamps."""


def to_cents(amount):
    return int(round(amount * 100))


def round_money(amount):
    return round(amount, 2)


def clamp_nonneg(amount):
    return max(0.0, amount)


def split_even(total, parts):
    cents = to_cents(total)
    base = cents // parts
    shares = [base] * parts
    for i in range(cents - base * parts):
        shares[i] = shares[i] + 1
    return [s / 100 for s in shares]


def apply_surcharge(subtotal, surcharge):
    total = subtotal + surcharge
    total = round(total)
    return total
''',
"ledgerkit/tax.py": '''\
"""VAT and per-unit pricing."""

VAT = 0.19


def gross(net, rate=VAT):
    return net * (1 + rate)


def per_unit(total, units):
    return total / units


def is_exempt(code):
    return code.startswith("EX-")


def rate_for(code, rates):
    return rates.get(code, VAT)
''',
"ledgerkit/discounts.py": '''\
"""Quantity and amount based discounts."""

BULK_MIN = 10


def bulk_rate(qty):
    if qty >= BULK_MIN:
        return 0.15
    return 0.0


def tiered(amount):
    if amount < 100:
        return 0.0
    return 0.05


def best_of(a, b):
    return max(a, b)
''',
"ledgerkit/inventory.py": '''\
"""Stock items and reorder logic."""


class Item:
    def __init__(self, sku, name, qty, reorder_at):
        self.sku = sku
        self.name = name
        self.qty = qty
        self.reorder_at = reorder_at


def sku_of(item):
    return item.sku


def needs_reorder(item):
    return item.qty <= item.reorder_at


def restock(items, sku, amount):
    for it in items:
        if it.sku == sku:
            it.qty += amount
    return items


def is_taxable(item):
    return item.get("taxable", True)
''',
"ledgerkit/schedule.py": '''\
"""Billing periods."""


def days_between(start, end):
    return end - start


def period_len(start, end):
    return days_between(start, end) + 1


def in_period(day, start, end):
    return start <= day <= end
''',
"ledgerkit/text.py": '''\
"""Import-file parsing."""


def parse_line(line):
    parts = line.split(",")
    return [p.strip() for p in parts]


def tail_fields(fields):
    return fields[1:]


def fee(n):
    return n * 2 - 1
''',
"tests/test_money.py": '''\
from ledgerkit.money import (apply_surcharge, clamp_nonneg, round_money,
                             split_even, to_cents)


def test_to_cents():
    assert to_cents(12.34) == 1234


def test_round_money():
    assert round_money(10.456) == 10.46
    assert round_money(3.005) == 3.0 or round_money(3.005) == 3.01


def test_clamp_nonneg():
    assert clamp_nonneg(-3.0) == 0.0
    assert clamp_nonneg(2.5) == 2.5


def test_split_even():
    assert split_even(10.0, 3) == [3.34, 3.33, 3.33]


def test_apply_surcharge():
    assert apply_surcharge(10.4, 0.3) == 11
    assert apply_surcharge(2.2, 0.2) == 2
''',
"tests/test_tax.py": '''\
from ledgerkit.tax import gross, is_exempt, per_unit, rate_for


def test_gross():
    assert gross(100, 0.25) == 125.0
    assert round(gross(100), 2) == 119.0


def test_per_unit():
    assert per_unit(10, 4) == 2.5


def test_is_exempt():
    assert is_exempt("EX-9") is True
    assert is_exempt("TX-9") is False


def test_rate_for():
    assert rate_for("food", {"food": 0.07}) == 0.07
    assert rate_for("other", {"food": 0.07}) == 0.19
''',
"tests/test_discounts.py": '''\
from ledgerkit.discounts import best_of, bulk_rate, tiered


def test_bulk_rate_boundary():
    assert bulk_rate(10) == 0.15
    assert bulk_rate(9.5) == 0.0
    assert bulk_rate(11) == 0.15


def test_tiered():
    assert tiered(50) == 0.0
    assert tiered(250) == 0.05
    assert tiered(100) == 0.05


def test_best_of():
    assert best_of(0.1, 0.2) == 0.2
''',
"tests/test_inventory.py": '''\
from ledgerkit.inventory import Item, is_taxable, needs_reorder, restock, sku_of


def test_sku_of():
    assert sku_of(Item("A1", "Anvil", 4, 2)) == "A1"


def test_needs_reorder():
    assert needs_reorder(Item("A1", "Anvil", 2, 2)) is True
    assert needs_reorder(Item("A1", "Anvil", 3, 2)) is False


def test_restock():
    items = restock([Item("A1", "Anvil", 4, 2)], "A1", 6)
    assert items[0].qty == 10


def test_is_taxable():
    assert is_taxable({}) is True
    assert is_taxable({"taxable": False}) is False
''',
"tests/test_schedule.py": '''\
from ledgerkit.schedule import days_between, in_period, period_len


def test_days_between():
    assert days_between(3, 10) == 7


def test_period_len():
    assert period_len(3, 10) == 8


def test_in_period():
    assert in_period(5, 3, 10) is True
''',
"tests/test_text.py": '''\
from ledgerkit.text import fee, parse_line, tail_fields


def test_parse_line():
    assert parse_line("a, b,c") == ["a", "b", "c"]


def test_tail_fields():
    assert tail_fields(["a", "b", "c"]) == ["b", "c"]


def test_fee():
    assert fee(2) == 3
''',
}


def main():
    root = sys.argv[1]
    if os.path.exists(root):
        raise SystemExit(f"refusing to overwrite {root}")
    for rel, body in FILES.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(body)
    g = lambda *a: subprocess.run(["git", "-C", root, *a], check=True,
                                  capture_output=True, text=True)
    g("init", "-q", "-b", "main")
    g("add", "-A")
    g("commit", "-q", "-m", "ledgerkit 1.4.2: money, tax, discounts, inventory, schedule, text")
    print(root, g("rev-parse", "--short", "HEAD").stdout.strip())


if __name__ == "__main__":
    main()
