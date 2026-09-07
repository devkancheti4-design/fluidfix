#!/bin/sh
# ATTACK 4: two guards, swept start offsets. Looking for the run whose
# `finally: _write(path, src)` writes a STALE snapshot over the other run's
# shipped repair (or over the other run's candidate).
set -u
D="$(cd "$(dirname "$0")" && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
: > "$D/out/a4.summary"
for OFF in 1.0 3.0 5.0 7.0 9.0; do
  R="$D/work/a4-$OFF"
  rm -rf "$R"; cp -R "$D/fixture/victim" "$R"
  "$D/tmo" 180 "$FF" guard "$R" > "$D/out/a4-$OFF.A.log" 2>&1 &
  APID=$!
  perl -e "select(undef,undef,undef,$OFF)"
  "$D/tmo" 180 "$FF" guard "$R" --budget 14 > "$D/out/a4-$OFF.B.log" 2>&1 &
  BPID=$!
  wait $APID; RA=$?
  wait $BPID; RB=$?
  L10="$(sed -n '10p' "$R/vpkg/calc.py")"
  cp "$R/vpkg/calc.py" "$D/out/a4-$OFF.final.py"
  # is the final file green?
  "$D/tmo" 90 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python -m pytest -q "$R" \
      > "$D/out/a4-$OFF.suite.log" 2>&1
  SR=$?
  AS="$(grep -c 'repaired line' "$D/out/a4-$OFF.A.log" || true)"
  BS="$(grep -c 'repaired line' "$D/out/a4-$OFF.B.log" || true)"
  printf 'off=%-4s A_rc=%s A_shipped=%s | B_rc=%s B_shipped=%s | final_line10=%-24s final_suite_rc=%s\n' \
     "$OFF" "$RA" "$AS" "$RB" "$BS" "$(echo $L10)" "$SR" >> "$D/out/a4.summary"
done
cat "$D/out/a4.summary"
