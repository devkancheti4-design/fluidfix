#!/bin/sh
# Build the Python victim repos. Idempotent: wipes and recreates fixtures/py.
set -e
D="$(cd "$(dirname "$0")/.." && pwd)"
F="$D/fixtures/py"
rm -rf "$F"; mkdir -p "$F"

mk() { mkdir -p "$F/$1/pkg" "$F/$1/tests"; : > "$F/$1/pkg/__init__.py"; }

# ---------------------------------------------------------------- py01_green
mk py01_green
cat > "$F/py01_green/pkg/mod.py" <<'EOF'
def diff(a, b):
    return b - a
EOF
cat > "$F/py01_green/tests/test_mod.py" <<'EOF'
from pkg.mod import diff
def test_diff():
    assert diff(2, 5) == 3
EOF

# ------------------------------------------------------------ py02_outofvocab
# A genuine out-of-vocabulary defect: the wrong function is called.
mk py02_outofvocab
cat > "$F/py02_outofvocab/pkg/mod.py" <<'EOF'
def scale(xs):
    return sorted(xs)
EOF
cat > "$F/py02_outofvocab/tests/test_mod.py" <<'EOF'
from pkg.mod import scale
def test_scale():
    assert scale([1, 2, 3]) == [2, 4, 6]
EOF

# --------------------------------------------------------- py03_amb_two_sites
# Compensating repair available at a second site (classic AMB).
mk py03_amb_two_sites
cat > "$F/py03_amb_two_sites/pkg/mod.py" <<'EOF'
def base(n):
    return n + 1
def total(n):
    return base(n) + 1
EOF
cat > "$F/py03_amb_two_sites/tests/test_mod.py" <<'EOF'
from pkg.mod import total
def test_total():
    assert total(3) == 3
EOF

# ------------------------------------------------------ py04_amb_one_site_spell
# Two SPELLINGS of one program at one site: `>= 10` vs `> 9`.
mk py04_amb_one_site_spell
cat > "$F/py04_amb_one_site_spell/pkg/mod.py" <<'EOF'
def big(units):
    if units >= 11:
        return "big"
    return "small"
EOF
cat > "$F/py04_amb_one_site_spell/tests/test_mod.py" <<'EOF'
from pkg.mod import big
def test_big():
    assert big(10) == "big"
    assert big(9) == "small"
EOF

# --------------------------------------------------------- py05_capped_green
# The lead: a green is found on the FIRST observation (line 2), then 18
# padding lines keep the search busy, so a --budget cut leaves the search
# CAPPED with a passing candidate already in hand.
mk py05_capped_green
/usr/bin/python3 - "$F/py05_capped_green/pkg/mod.py" <<'PYGEN'
import sys
L = ["def diff(a, b):", "    r = a - b"]      # line 2: correct is  r = b - a
for i in range(1, 19):
    L.append(f"    pad = {i} * 2 + {i}")
L.append("    return r")
open(sys.argv[1], "w").write("\n".join(L) + "\n")
PYGEN
cat > "$F/py05_capped_green/tests/test_mod.py" <<'EOF'
import time
from pkg.mod import diff
def test_diff():
    time.sleep(0.30)
    assert diff(2, 5) == 3
EOF

# --------------------------------------------------------------- py08b_over64
# >64 rejected candidates, so loop.py's tried_log cap bites and tried_more>0.
mk py08b_over64
/usr/bin/python3 - "$F/py08b_over64/pkg/mod.py" <<'PYGEN'
import sys
L = ["def total():", "    s = 0"]
for i in range(1, 61):
    L.append(f"    s = s + {i * 3}")
L.append("    return s + 1")
open(sys.argv[1], "w").write("\n".join(L) + "\n")
PYGEN
cat > "$F/py08b_over64/tests/test_mod.py" <<'EOF'
from pkg.mod import total
def test_total():
    assert total() == 424242
EOF

# ------------------------------------------------------ py08_many_rejections
# >64 rejected candidates so tried_more > 0.
mk py08_many_rejections
python3 - "$F/py08_many_rejections/pkg/mod.py" <<'EOF'
import sys
lines = ["def total():", "    s = 0"]
for i in range(1, 30):
    lines.append(f"    s = s + {i * 3}")
lines.append("    return s + 1")
open(sys.argv[1], "w").write("\n".join(lines) + "\n")
EOF
cat > "$F/py08_many_rejections/tests/test_mod.py" <<'EOF'
from pkg.mod import total
def test_total():
    assert total() == 99999
EOF

# ------------------------------------------------------------- py09_no_tests
mkdir -p "$F/py09_no_tests/pkg" "$F/py09_no_tests/tests"
: > "$F/py09_no_tests/pkg/__init__.py"
cat > "$F/py09_no_tests/pkg/mod.py" <<'EOF'
def diff(a, b):
    return a - b
EOF

echo "built:"; ls "$F"

for r in "$F"/*; do
  printf '[pytest]\npythonpath = .\n' > "$r/pytest.ini"
done
echo "pytest.ini written"
