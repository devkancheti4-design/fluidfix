#!/bin/sh
# ATTACK 1: a user edits the target file WHILE a guard is searching.
# fluidfix reads the file once into `src` and every rollback writes that
# in-memory snapshot back. A concurrent user edit should be clobbered.
set -e
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
R="$D/work/a1"
rm -rf "$R"; cp -R "$D/fixture/victim" "$R"

shasum -a 256 "$R/vpkg/calc.py" > "$D/out/a1.before.sha"
cp "$R/vpkg/calc.py" "$D/out/a1.before.py"

"$D/tmo" 180 "$FF" guard "$R" > "$D/out/a1.guard.log" 2>&1 &
GPID=$!

# simulate the user typing at t+4s (mid-search, after >=2 suite runs)
perl -e 'select(undef,undef,undef,4.0)'
cat >> "$R/vpkg/calc.py" <<'PYEOF'


def tax(amount):
    """USER EDIT: written by the human at t+4s, while the guard was running."""
    return amount * 0.08
PYEOF
cp "$R/vpkg/calc.py" "$D/out/a1.useredit.py"
echo "[driver] user edit applied at t+4s" >> "$D/out/a1.guard.log"

wait $GPID; echo "[driver] guard rc=$?" >> "$D/out/a1.guard.log"
cp "$R/vpkg/calc.py" "$D/out/a1.after.py"
