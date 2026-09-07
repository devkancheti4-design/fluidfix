#!/bin/sh
# UNTUNED sweep: every (PERIOD, OFFSET) phase of a periodic flake, DEFAULT
# FLUIDFIX_CONFIRM (unset => 1).  Victim A2: no correct repair exists, so
# every "repaired" outcome is a WRONG repair shipped.
D=$(cd "$(dirname "$0")/.." && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv
for P in 2 3 4 5 6 7 8; do
  O=0
  while [ "$O" -lt "$P" ]; do
    V="$D/fixtures/psweep/p${P}_o${O}"
    "$D/bin/build_victim.sh" "$V" A2
    cp "$D/fixtures/period/conftest.py" "$V/conftest.py"
    VICTIM_PERIOD=$P VICTIM_OFFSET=$O \
      "$D/bin/run.sh" 300 "$PY/bin/fluidfix" repair "$V" --file money.py --json \
      > "$D/logs/psweep_p${P}_o${O}.json" 2>&1
    OUT=$("$PY/bin/python" - "$D/logs/psweep_p${P}_o${O}.json" <<'PYX'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("NON-JSON: " + open(sys.argv[1]).read().strip()[:100].replace("\n", " "))
else:
    print(("SHIPPED-WRONG " + repr(d["new_line"].strip())) if d["repaired"]
          else "REFUSED " + d["reason"][:90].replace("\n", " "))
PYX
)
    printf 'PERIOD=%s OFFSET=%s  %s\n' "$P" "$O" "$OUT"
    O=$((O + 1))
  done
done
