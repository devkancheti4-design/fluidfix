#!/bin/bash
# After BENCH_DONE and the three source fixes: every replay, one job at a time, on the diagnostic clone set.
set -u; D=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
echo "== source under test: $(git -C /Users/kanchetidevieswar/neo/fluidfix rev-parse --short HEAD) + uncommitted fixes 1-3 (harness paths, SCARCE from taught, timeout hint) =="
./clean_pass.sh "$D" arrow
ONLY900=1 ./clean_pass.sh "$D" python-sortedcontainers
./clean_pass.sh "$D" rich
echo "== click/cmp-1 with the timeout advice followed =="; python3 rerun_budget.py "$D" click/cmp-1 --budget 300 --extra "--test-timeout 10" --tag _tt10
echo "== rescans (string-aware sites) =="; python3 bench_rescan.py "$D" rich cmp; python3 bench_rescan.py "$D" rich lit _unicode_data
python3 report.py; echo CLEAN_CHAIN_DONE
