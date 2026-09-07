#!/bin/sh
# ATTACK 2: two guards on ONE repo at the same time.
# There is no lock. Each reads its own `src` snapshot, each writes
# .fluidfix/inflight.json, each calls end_inflight() in its finally block,
# and guard B's recover_inflight() runs while guard A is mid-candidate.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
R="$D/work/a2"
rm -rf "$R"; cp -R "$D/fixture/victim" "$R"
cp "$R/vpkg/calc.py" "$D/out/a2.before.py"

# journal watcher: sample .fluidfix/inflight.json + the file every 250ms
( i=0; while [ $i -lt 200 ]; do
    if [ -f "$R/.fluidfix/inflight.json" ]; then
      printf '%s J=%s LINE10=%s\n' "$(date +%H:%M:%S.$(printf %03d $((i*250%1000))))" \
        "$(shasum -a 256 "$R/.fluidfix/inflight.json" | cut -c1-12)" \
        "$(sed -n '10p' "$R/vpkg/calc.py" 2>/dev/null | tr -d '\n')"
    else
      printf '%s J=-none-      LINE10=%s\n' "$(date +%H:%M:%S)" \
        "$(sed -n '10p' "$R/vpkg/calc.py" 2>/dev/null | tr -d '\n')"
    fi
    i=$((i+1)); perl -e 'select(undef,undef,undef,0.25)'
  done ) > "$D/out/a2.journal.trace" 2>&1 &
WPID=$!

"$D/tmo" 180 "$FF" guard "$R" > "$D/out/a2.guardA.log" 2>&1 &
APID=$!
perl -e 'select(undef,undef,undef,4.0)'     # B starts mid-A
"$D/tmo" 180 "$FF" guard "$R" > "$D/out/a2.guardB.log" 2>&1 &
BPID=$!

wait $APID; RA=$?; echo "[driver] guard A rc=$RA" >> "$D/out/a2.guardA.log"
wait $BPID; RB=$?; echo "[driver] guard B rc=$RB" >> "$D/out/a2.guardB.log"
kill $WPID 2>/dev/null || true
cp "$R/vpkg/calc.py" "$D/out/a2.after.py"
ls -la "$R/.fluidfix" > "$D/out/a2.fluidfix.ls" 2>&1 || echo "no .fluidfix" > "$D/out/a2.fluidfix.ls"
