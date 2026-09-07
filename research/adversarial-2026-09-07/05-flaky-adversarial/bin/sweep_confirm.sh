#!/bin/sh
# Sweep FLUIDFIX_CONFIRM x quarantine COOLDOWN on victim A2.
D=$(cd "$(dirname "$0")/.." && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv
for CONF in 0 1 2 3; do
  for COOL in 2 4 6 8; do
    V="$D/fixtures/sweep/c${CONF}_k${COOL}"
    "$D/bin/build_victim.sh" "$V" A2
    FLUIDFIX_CONFIRM=$CONF VICTIM_COOLDOWN=$COOL \
      "$D/bin/run.sh" 300 "$PY/bin/fluidfix" repair "$V" --file money.py --json \
      > "$D/logs/sweep_c${CONF}_k${COOL}.json" 2>&1
    NEW=$("$PY/bin/python" -c "
import json,sys
try:
    d=json.load(open('$D/logs/sweep_c${CONF}_k${COOL}.json'))
except Exception as e:
    print('PARSE-FAIL'); sys.exit()
print(('SHIPPED '+repr(d['new_line'].strip())) if d['repaired'] else ('REFUSED '+d['reason'][:110].replace(chr(10),' ')))
")
    printf 'CONFIRM=%s COOLDOWN=%s  %s\n' "$CONF" "$COOL" "$NEW"
  done
done
