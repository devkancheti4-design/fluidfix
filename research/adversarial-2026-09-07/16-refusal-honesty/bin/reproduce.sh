#!/bin/sh
# Reruns the four headline refusal-honesty attacks. ~3 minutes.
# Every fluidfix invocation goes through bin/run (nice -n 15 + perl alarm).
set -e
D="$(cd "$(dirname "$0")/.." && pwd)"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src

sh "$D/bin/make_py_fixtures.sh" >/dev/null 2>&1 || true   # py01..py09 only
echo "=================== F1  python: green in hand, reported as REFUTED"
cd "$D/fixtures/py/py05_capped_green"; cp "$D/pristine/py05_mod.py" pkg/mod.py
"$D/bin/run" 300 $FF guard . --budget 30 || true
echo "--- what repair() actually returned at the same deadline ---"
cp "$D/pristine/py05_mod.py" pkg/mod.py
"$D/bin/run" 300 $PY "$D/bin/probe_capped.py" . pkg/mod.py 30
cp "$D/pristine/py05_mod.py" pkg/mod.py

echo "=================== F2  python: clock, reported as vocabulary gap"
"$D/bin/run" 300 $FF guard . --budget 6 || true
cp "$D/pristine/py05_mod.py" pkg/mod.py
"$D/bin/run" 300 $PY "$D/bin/probe_capped.py" . pkg/mod.py 6
cp "$D/pristine/py05_mod.py" pkg/mod.py

echo "=================== F3  C: 'nothing pointed at a file' with two frames printed"
"$D/bin/c01_cmd.sh" --budget 2 || true
echo "--- the failing output the claim is about ---"
( cd "$D/fixtures/c/c01_frame" && ./build/tests || true )

echo "=================== F4  C: green in hand, reported as vocabulary gap"
"$D/bin/c02_cmd.sh" --budget 15 || true
cd "$D/fixtures/c/c02_capped_green"; cp "$D/pristine/c02_mathops.c" src/mathops.c
"$D/bin/run" 300 $PY "$D/bin/probe_capped_c.py" . src/mathops.c \
   'cc -O0 -o build/tests src/mathops.c tests/test_main.c' './build/tests' 15
cp "$D/pristine/c02_mathops.c" src/mathops.c

echo "=================== F5  python: rejected-candidate count"
cd "$D/fixtures/py/py08b_over64"; cp "$D/pristine/py08b_mod.py" pkg/mod.py
"$D/bin/run" 900 $FF guard . || true
"$D/bin/run" 900 $PY "$D/bin/probe_counts.py" . pkg/mod.py
cp "$D/pristine/py08b_mod.py" pkg/mod.py
