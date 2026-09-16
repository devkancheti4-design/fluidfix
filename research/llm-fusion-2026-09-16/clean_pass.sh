#!/bin/bash
# Uncontended replays, one at a time, after BENCH_DONE.
#   ./clean_pass.sh <repos_ladder-dir> arrow                 -> every saved arrow case at 300 s (the bench's arrow
#                                                              trials ran under load), then 900 s for budget-limited ones
#   ONLY900=1 ./clean_pass.sh <dir> python-sortedcontainers rich -> only the 900 s follow-ups, decided from the bench's
#                                                              own refusal hint (those trials ran with <=1 other job)
set -u; L=$1; shift; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
budget_limited() { python3 -c "import json,sys; r=json.load(open('$1')); h=r.get('hint',''); sys.exit(0 if r.get('verdict','REFUSED')=='REFUSED' and ('budget' in h or 'cut short' in h or 'CAPPED' in h or 'RAISE_BUDGET' in h) else 1)"; }
for R in "$@"; do
  if [ -z "${ONLY900:-}" ]; then
    for d in cases/$R/*/; do c="$R/$(basename $d)"; echo "== clean 300 s: $c =="; python3 rerun_budget.py "$L" "$c" --budget 300; done
  fi
  for d in cases/$R/*/; do c="$R/$(basename $d)"
    f="$d/rerun_budget300.json"; [ -f "$f" ] || f="$d/refusal_tier0.json"; [ -f "$f" ] || continue
    if budget_limited "$f"; then echo "== clean 900 s (budget-limited): $c =="; python3 rerun_budget.py "$L" "$c" --budget 900; fi
  done
done
echo CLEAN_PASS_DONE
