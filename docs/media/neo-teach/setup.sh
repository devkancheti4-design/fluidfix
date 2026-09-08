#!/bin/zsh
# Rebuilds the demo repo to the exact state the recording starts from:
# a green project with one regression commit on top of it. Nothing is
# pre-repaired; every fluidfix run in the video happens live on camera.
set -e
ROOT="$1"; rm -rf "$ROOT"; mkdir -p "$ROOT/shipwise" "$ROOT/tests"; cd "$ROOT"
: > shipwise/__init__.py
cat > shipwise/rates.py <<'EOF'
ZONES = {"domestic": 4.20, "eu": 9.80, "world": 18.50}
EXPRESS_FACTOR = 1.6


def zone_rate(zone):
    return ZONES[zone]
EOF
cat > shipwise/quote.py <<'EOF'
from .rates import EXPRESS_FACTOR, zone_rate


def quote(weight_kg, zone, express=False):
    total = weight_kg * zone_rate(zone)
    if express:
        total = total * EXPRESS_FACTOR
    return round(total, 2)
EOF
cat > shipwise/invoice.py <<'EOF'
from .quote import quote

VAT = 0.19


def invoice_total(shipments):
    net = sum(quote(w, z) for w, z in shipments)
    gross = net * (1 + VAT)
    return round(gross, 2)
EOF
cat > tests/test_quote.py <<'EOF'
from shipwise.quote import quote


def test_domestic():
    assert quote(2.5, "domestic") == 10.5


def test_express_eu():
    assert quote(1.3, "eu", express=True) == 20.38
EOF
cat > tests/test_invoice.py <<'EOF'
from shipwise.invoice import invoice_total


def test_invoice():
    assert invoice_total([(2.5, "domestic"), (1.0, "world")]) == 34.51
EOF
cat > pyproject.toml <<'EOF'
[project]
name = "shipwise"
version = "0.3.1"

[tool.pytest.ini_options]
pythonpath = ["."]
EOF
printf '__pycache__/\n.pytest_cache/\n.fluidfix/\n' > .gitignore
git init -q -b main
git add -A
git commit -qm "shipwise: quotes, invoices, tests"
sed -i '' 's/net \* (1 + VAT)/net * (1 - VAT)/' shipwise/invoice.py
git commit -qam "invoice: tidy the vat formula"
echo "demo repo ready at $ROOT"; git log --oneline
