#!/bin/zsh
# Rerun every attempt in ATTACK.md. ~90s total, one run at a time, nice -n 15,
# each wrapped in run.sh (this machine has no coreutils `timeout`).
set -u
cd "$(dirname "$0")"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
R() { rm -rf fixtures/$1 && cp -R fixtures_pristine/$1 fixtures/; }

echo "== 1  what does register() validate? =="
./run.sh 60 $PY probe_register.py

echo "\n== 2  S1a CONTROL: repoF, no dictionary (fluidfix repairs it CORRECTLY) =="
R repoF_preempt; ./run.sh 180 $FF guard fixtures/repoF_preempt; cat fixtures/repoF_preempt/orders.py

echo "\n== 3  S1a: repoF + poison_wrong.py (WRONG worked example wins) =="
R repoF_preempt; ./run.sh 180 $FF guard fixtures/repoF_preempt --dictionary fixtures/poison_wrong.py
cat fixtures/repoF_preempt/orders.py
(cd fixtures/repoF_preempt && $PY -c "import orders; print('refund(4,10) =', orders.refund(4,10), '-- correct is -6')")

echo "\n== 4  S1b: repoC + poison_class.py (whole-file SpanEdit, far-away edit) =="
R repoC_unrelated; ./run.sh 180 $FF guard fixtures/repoC_unrelated --dictionary fixtures/poison_class.py
diff fixtures_pristine/repoC_unrelated/ledger.py fixtures/repoC_unrelated/ledger.py

echo "\n== 5  persistence: the SAME class, a DIFFERENT repo, zero new examples =="
R repoD_generalise; ./run.sh 180 $FF guard fixtures/repoD_generalise --dictionary fixtures/poison_class.py
diff fixtures_pristine/repoD_generalise/shipping.py fixtures/repoD_generalise/shipping.py

echo "\n== 6  DEFENCE: every poisoned dictionary against a HEALTHY repo =="
for D in poison_wrong.py poison_class.py poison_kill.py poison_crash.py poison_none.py; do
  R repoB_healthy
  ./run.sh 180 $FF guard fixtures/repoB_healthy --dictionary fixtures/$D 2>&1 | tail -2
  diff -r --exclude=.fluidfix --exclude=__pycache__ \
       fixtures_pristine/repoB_healthy fixtures/repoB_healthy >/dev/null \
       && echo "  $D -> repo byte-identical" || echo "  $D -> REPO CHANGED"
done

echo "\n== 7  DEFENCE: kind-3 collision disables a shipped class, but says so =="
R repoG_additive; ./run.sh 180 $FF guard fixtures/repoG_additive
R repoG_additive; ./run.sh 180 $FF guard fixtures/repoG_additive --dictionary fixtures/poison_kill.py
diff fixtures_pristine/repoG_additive/calc.py fixtures/repoG_additive/calc.py && echo "  tree byte-identical after the denial"

echo "\n== 8  DEFENCE: a teacher that raises / returns None =="
for D in poison_crash.py poison_none.py; do
  R repoG_additive
  ./run.sh 180 $FF guard fixtures/repoG_additive --dictionary fixtures/$D 2>&1 | tail -3
  diff fixtures_pristine/repoG_additive/calc.py fixtures/repoG_additive/calc.py \
    && echo "  $D -> tree byte-identical"
done

echo "\n== 9  the observation byte behind S1a =="
./run.sh 240 $PY probe_byte.py
