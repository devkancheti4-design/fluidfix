#!/bin/sh
# Same flake against the UNATTENDED path (`fluidfix guard`), default CONFIRM.
D=$(cd "$(dirname "$0")/.." && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv
for S in 4 5 6 7 8; do
  for K in 2 4 6; do
    V="$D/fixtures/gsweep/s${S}_k${K}"
    "$D/bin/build_victim.sh" "$V" A2
    VICTIM_STRIKES=$S VICTIM_COOLDOWN=$K \
      "$D/bin/run.sh" 300 "$PY/bin/fluidfix" guard "$V" \
      > "$D/logs/gsweep_s${S}_k${K}.txt" 2>&1
    D1=$(diff "$V/money.py.pristine" "$V/money.py" > /dev/null 2>&1 && echo "tree-clean" || echo "TREE-CHANGED")
    printf 'STRIKES=%s COOLDOWN=%s  %s | %s\n' "$S" "$K" "$D1" \
      "$(head -1 "$D/logs/gsweep_s${S}_k${K}.txt" | cut -c1-100)"
  done
done
