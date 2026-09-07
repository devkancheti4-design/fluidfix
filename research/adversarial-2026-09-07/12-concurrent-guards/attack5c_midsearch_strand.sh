#!/bin/sh
# ATTACK 5c: catch the window while guard A is STILL SEARCHING (A alive), the
# journal has been deleted by guard B, and a RED candidate is on disk.
# SIGKILL there: the repo keeps fluidfix's wrong mutation with no journal.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
ORIG='    if score > 60:'
: > "$D/out/a5d.trials"
T=1
while [ $T -le 4 ]; do
  R="$D/work/a5d-$T"; rm -rf "$R"; cp -R "$D/fixture/victim-red" "$R"
  J="$R/.fluidfix/inflight.json"; F="$R/vpkg/calc.py"
  nice -n 15 "$FF" guard "$R" > "$D/out/a5d-$T.A.log" 2>&1 & APID=$!
  i=0; while [ $i -lt 900 ]; do [ -f "$J" ] && break; i=$((i+1)); perl -e 'select(undef,undef,undef,0.05)'; done
  echo "trial $T: A journalled" >> "$D/out/a5d.trials"
  nice -n 15 "$FF" guard "$R" > "$D/out/a5d-$T.B.log" 2>&1 & BPID=$!
  HIT=0; i=0
  while [ $i -lt 3000 ]; do
    kill -0 $APID 2>/dev/null || break          # A finished: window closed
    L="$(sed -n '10p' "$F" 2>/dev/null)"
    if [ ! -f "$J" ] && [ -n "$L" ] && [ "$L" != "$ORIG" ]; then
      HIT=1
      kill -KILL $APID $BPID 2>/dev/null
      pkill -KILL -P $APID 2>/dev/null; pkill -KILL -P $BPID 2>/dev/null
      pkill -KILL -f "$R" 2>/dev/null
      echo "  window hit: A ALIVE, journal ABSENT, disk holds: $L" >> "$D/out/a5d.trials"
      break
    fi
    i=$((i+1)); perl -e 'select(undef,undef,undef,0.02)'
  done
  kill -KILL $APID $BPID 2>/dev/null; wait $APID 2>/dev/null; wait $BPID 2>/dev/null
  perl -e 'select(undef,undef,undef,1.2)'; pkill -KILL -f "$R" 2>/dev/null
  L10="$(sed -n '10p' "$F")"; JP="$([ -f "$J" ] && echo yes || echo no)"
  "$D/tmo" 120 "$PY" -m pytest -q "$R" > "$D/out/a5d-$T.suite.log" 2>&1; SR=$?
  cp "$F" "$D/out/a5d-$T.stranded.py"
  printf 'trial=%s hit=%s journal=%s line10=%-26s suite_rc=%s\n' \
     "$T" "$HIT" "$JP" "$(echo $L10)" "$SR" >> "$D/out/a5d.trials"
  if [ "$JP" = no ] && [ "$SR" != 0 ]; then
     echo "  *** STRANDED RED MUTATION, NO JOURNAL (trial $T) ***" >> "$D/out/a5d.trials"
     cp "$F" "$D/out/a5d.final.py"; break
  fi
  T=$((T+1))
done
cat "$D/out/a5d.trials"
