#!/bin/sh
# UNTUNED sweep of the quarantine flake at DEFAULT FLUIDFIX_CONFIRM (=1).
# Victim A2 has NO correct repair in the vocabulary, so any "repaired"
# outcome is a WRONG repair written to disk.
D=$(cd "$(dirname "$0")/.." && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv
for S in 1 2 3 4 5 6; do
  for K in 1 2 3 4 5 6; do
    V="$D/fixtures/qsweep/s${S}_k${K}"
    "$D/bin/build_victim.sh" "$V" A2
    VICTIM_STRIKES=$S VICTIM_COOLDOWN=$K \
      "$D/bin/run.sh" 300 "$PY/bin/fluidfix" repair "$V" --file money.py --json \
      > "$D/logs/qsweep_s${S}_k${K}.json" 2>&1
    OUT=$("$PY/bin/python" - "$D/logs/qsweep_s${S}_k${K}.json" <<'PYX'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("GATED  " + open(sys.argv[1]).read().strip()[:70].replace("\n", " "))
else:
    print(("SHIPPED-WRONG " + repr(d["new_line"].strip())) if d["repaired"]
          else "REFUSED " + d["reason"][:70].replace("\n", " "))
PYX
)
    printf 'STRIKES=%s COOLDOWN=%s  %s\n' "$S" "$K" "$OUT"
  done
done
