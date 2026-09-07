#!/bin/sh
# Rebuilds repo-dirtyindex2 (F2): a repo whose HEAD carries the regression and
# whose user has unrelated work STAGED but not committed.
set -e
D="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$D/repo-dirtyindex2"; mkdir -p "$D/repo-dirtyindex2"; cd "$D/repo-dirtyindex2"
cat > billing.py <<'EOF'
def late_fee(days):
    if days >= 30:
        return 25
    return 0
EOF
cat > shipping.py <<'EOF'
def cost(weight):
    return weight * 2
EOF
cat > test_billing.py <<'EOF'
from billing import late_fee


def test_late_fee():
    assert late_fee(31) == 25
    assert late_fee(30) == 0
    assert late_fee(0) == 0
EOF
git init -q .
git -c user.name=u -c user.email=u@e.invalid add -A
git -c user.name=u -c user.email=u@e.invalid commit -q -m "feat: late fees (this commit carries the regression)"
cat > shipping.py <<'EOF'
def cost(weight):
    # WIP: half-finished rewrite, staged so I do not lose it. NOT ready to ship.
    return weight * 2 + surcharge(weight)   # surcharge() does not exist yet
EOF
printf 'TODO: private scratch notes, staged by accident with `git add -A`\n' > secrets_wip.txt
git add shipping.py secrets_wip.txt
git config user.name u; git config user.email u@e.invalid
echo "--- status before ---"; git status --short
echo "--- now run: ---"
echo "  $D/bin/tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --commit --budget 120"
echo "  git show --stat HEAD    # expect secrets_wip.txt and shipping.py swept in"
