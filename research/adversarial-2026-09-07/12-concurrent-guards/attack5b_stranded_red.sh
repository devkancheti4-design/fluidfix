#!/bin/sh
# ATTACK 5b: same window as 5, but keep trying until the stranded, UNJOURNALLED
# candidate is a RED one -- i.e. the repo is left with a broken suite and no
# record of what it used to be. Single-run invariant says this cannot happen.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
ORIG='    if units > 10:'
: > "$D/out/a5b.trials"
T=1
while [ $T -le 8 ]; do
  R="$D/work/a5b-$T"; rm -rf "$R"; cp -R "$D/fixture/victim" "$R"
  J="$R/.fluidfix/inflight.json"; F="$R/vpkg/calc.py"
  nice -n 15 "$FF" guard "$R" > "$D/out/a5b-$T.A.log" 2>&1 & APID=$!
  i=0; while [ $i -lt 400 ]; do [ -f "$J" ] && break; i=$((i+1)); perl -e 'select(undef,undef,undef,0.05)'; done
  nice -n 15 "$FF" guard "$R" > "$D/out/a5b-$T.B.log" 2>&1 & BPID=$!
  HIT=0; i=0
  while [ $i -lt 900 ]; do
    L="$(sed -n '10p' "$F" 2>/dev/null)"
    if [ ! -f "$J" ] && [ -n "$L" ] && [ "$L" != "$ORIG" ]; then
      HIT=1
      kill -KILL $APID $BPID 2>/dev/null
      pkill -KILL -P $APID 2>/dev/null; pkill -KILL -P $BPID 2>/dev/null
      pkill -KILL -f "$R" 2>/dev/null
      break
    fi
    i=$((i+1)); perl -e 'select(undef,undef,undef,0.02)'
  done
  wait $APID 2>/dev/null; wait $BPID 2>/dev/null
  perl -e 'select(undef,undef,undef,1.2)'; pkill -KILL -f "$R" 2>/dev/null
  L10="$(sed -n '10p' "$F")"
  JP="$([ -f "$J" ] && echo yes || echo no)"
  "$D/tmo" 90 "$PY" -m pytest -q "$R" > "$D/out/a5b-$T.suite.log" 2>&1; SR=$?
  cp "$F" "$D/out/a5b-$T.stranded.py"
  printf 'trial=%s window_hit=%s journal=%s line10=%-26s suite_rc=%s\n' \
     "$T" "$HIT" "$JP" "$(echo $L10)" "$SR" >> "$D/out/a5b.trials"
  if [ "$JP" = no ] && [ "$SR" != 0 ] && [ "$(echo $L10)" != "$(echo $ORIG)" ]; then
     echo "  *** STRANDED RED MUTATION, NO JOURNAL -- trial $T ***" >> "$D/out/a5b.trials"
     # does a later guard run recover the user's original? it cannot: no journal
     "$D/tmo" 180 "$FF" guard "$R" > "$D/out/a5b-$T.run3.log" 2>&1
     echo "  later guard rc=$?  line10 now: $(sed -n '10p' "$F")" >> "$D/out/a5b.trials"
     cp "$F" "$D/out/a5b.final.py"
     break
  fi
  T=$((T+1))
done
cat "$D/out/a5b.trials"
