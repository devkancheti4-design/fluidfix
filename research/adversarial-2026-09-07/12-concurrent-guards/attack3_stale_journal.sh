#!/bin/sh
# ATTACK 3: the crash journal has no staleness / ownership check.
# recover_inflight() blindly writes rec["original"] over whatever is on disk
# now. Kill run A mid-candidate, let the USER fix the bug by hand, then run
# the guard again: the user's fix is silently overwritten by the stale journal.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
R="$D/work/a3"
rm -rf "$R"; cp -R "$D/fixture/victim" "$R"

# ---- phase 1: start a guard and SIGKILL it once a candidate is on disk ----
nice -n 15 "$FF" guard "$R" > "$D/out/a3.run1.log" 2>&1 &
APID=$!
i=0
while [ $i -lt 240 ]; do
  if [ -f "$R/.fluidfix/inflight.json" ] && ! grep -q 'if units > 10:' "$R/vpkg/calc.py"; then
    kill -KILL -"$APID" 2>/dev/null || kill -KILL "$APID" 2>/dev/null
    pkill -KILL -P $APID 2>/dev/null
    break
  fi
  i=$((i+1)); perl -e 'select(undef,undef,undef,0.1)'
done
wait $APID 2>/dev/null
perl -e 'select(undef,undef,undef,1.0)'
pkill -KILL -f "$R" 2>/dev/null

echo "--- after SIGKILL ---"                       >  "$D/out/a3.state"
echo "journal present: $([ -f "$R/.fluidfix/inflight.json" ] && echo yes || echo no)" >> "$D/out/a3.state"
echo "line 10 on disk: $(sed -n '10p' "$R/vpkg/calc.py")" >> "$D/out/a3.state"
cp "$R/vpkg/calc.py" "$D/out/a3.after_kill.py"

# ---- phase 2: THE USER fixes the bug by hand and adds their own code ----
cat > "$R/vpkg/calc.py" <<'PYEOF'
"""A tiny module with one mechanical defect."""


def total(units, price):
    return units * price


def discount(units):
    # FIXED BY THE USER, by hand, after fluidfix died. Reviewed. Correct.
    if units >= 10:
        return 0.9
    return 1.0


def bill(units, price):
    return total(units, price) * discount(units)


def tax(amount):
    """USER CODE written after the crash. Not fluidfix's to touch."""
    return amount * 0.08
PYEOF
cp "$R/vpkg/calc.py" "$D/out/a3.user_fixed.py"
echo "--- user hand-fixed the file, suite is now GREEN ---" >> "$D/out/a3.state"
"$D/tmo" 90 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python -m pytest -q "$R" > "$D/out/a3.user_suite.log" 2>&1
echo "user's suite rc=$?" >> "$D/out/a3.state"

# ---- phase 3: the user runs the guard again ----
"$D/tmo" 180 "$FF" guard "$R" > "$D/out/a3.run2.log" 2>&1
echo "run2 rc=$?" >> "$D/out/a3.state"
cp "$R/vpkg/calc.py" "$D/out/a3.final.py"
