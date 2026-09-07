#!/bin/sh
# ATTACK 5: guard B's recover_inflight()/end_inflight() DELETES guard A's
# crash journal (there is no owner/pid field on the record). That opens a
# window a single run can never enter: A's candidate mutation is on disk with
# NO journal describing it. SIGKILL there and the mutation is permanent and
# unrecoverable -- the exact failure the journal exists to prevent.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
R="$D/work/a5"
rm -rf "$R"; cp -R "$D/fixture/victim" "$R"
J="$R/.fluidfix/inflight.json"
F="$R/vpkg/calc.py"
ORIG='    if units > 10:'

nice -n 15 "$FF" guard "$R" > "$D/out/a5.A.log" 2>&1 &
APID=$!
# wait for A to journal
i=0; while [ $i -lt 300 ]; do [ -f "$J" ] && break; i=$((i+1)); perl -e 'select(undef,undef,undef,0.05)'; done
echo "A journalled at poll $i" > "$D/out/a5.state"

nice -n 15 "$FF" guard "$R" > "$D/out/a5.B.log" 2>&1 &
BPID=$!

# poll for the impossible-in-a-single-run state:
#   file MUTATED  +  journal ABSENT
HIT=0; i=0
while [ $i -lt 600 ]; do
  L="$(sed -n '10p' "$F" 2>/dev/null)"
  if [ ! -f "$J" ] && [ -n "$L" ] && [ "$L" != "$ORIG" ]; then
     HIT=1
     echo "WINDOW HIT at poll $i: journal ABSENT, disk holds: $L" >> "$D/out/a5.state"
     kill -KILL $APID $BPID 2>/dev/null
     pkill -KILL -P $APID 2>/dev/null; pkill -KILL -P $BPID 2>/dev/null
     pkill -KILL -f "$R" 2>/dev/null
     break
  fi
  i=$((i+1)); perl -e 'select(undef,undef,undef,0.02)'
done
[ $HIT -eq 0 ] && echo "no window hit" >> "$D/out/a5.state"
wait $APID 2>/dev/null; wait $BPID 2>/dev/null
perl -e 'select(undef,undef,undef,1.5)'; pkill -KILL -f "$R" 2>/dev/null

echo "--- after SIGKILL of both ---"                                  >> "$D/out/a5.state"
echo "journal present: $([ -f "$J" ] && echo yes || echo no)"         >> "$D/out/a5.state"
echo "line 10 on disk: $(sed -n '10p' "$F")"                          >> "$D/out/a5.state"
cp "$F" "$D/out/a5.after_kill.py"
"$D/tmo" 90 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python -m pytest -q "$R" > "$D/out/a5.suite_after_kill.log" 2>&1
echo "suite after kill rc=$?" >> "$D/out/a5.state"

# can a later guard run recover it?
"$D/tmo" 180 "$FF" guard "$R" > "$D/out/a5.run3.log" 2>&1
echo "recovery run rc=$?" >> "$D/out/a5.state"
cp "$F" "$D/out/a5.final.py"
