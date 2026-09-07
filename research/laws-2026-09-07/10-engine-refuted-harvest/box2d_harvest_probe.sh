#!/bin/bash
# What does a C harvest entry carry for the recorded contact_solver.c defect?
# Builds a private COPY of Box2D (unit tests only), verifies green, injects the
# recorded defect at src/contact_solver.c:2032 (`constraints + wideIndex` ->
# `constraints - wideIndex`), runs the test binary once, and reproduces the
# `why` string COracle.check() would harvest. Restores the file afterwards.
set -u
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/10-engine-refuted-harvest
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
B=$D/box2d
cd $B || exit 1
echo "== configure =="
nice -n 15 $PY $D/tmo.py 300 cmake -S . -B build -DBOX2D_SAMPLES=OFF -DBOX2D_BENCHMARKS=OFF -DBOX2D_UNIT_TESTS=ON -DCMAKE_BUILD_TYPE=Release > $D/box2d_configure.log 2>&1; echo "configure rc=$?"
echo "== build (pristine) =="
/usr/bin/time -p nice -n 15 $PY $D/tmo.py 300 cmake --build build -j4 > $D/box2d_build.log 2>&1; echo "build rc=$?"; tail -2 $D/box2d_build.log
echo "== pristine run =="
nice -n 15 $PY $D/tmo.py 120 ./build/bin/test > $D/box2d_pristine.log 2>&1; echo "pristine rc=$?"; grep -c "test passed" $D/box2d_pristine.log; grep -i "fail\|All Box2D" $D/box2d_pristine.log | head -5
echo "== inject defect at src/contact_solver.c:2032 =="
cp src/contact_solver.c $D/contact_solver.c.orig
sed -n 2032p src/contact_solver.c
$PY - <<'PYEOF'
p="src/contact_solver.c"; L=open(p,encoding="utf-8",newline="").read().split("\n")
assert "constraints + wideIndex" in L[2031], L[2031]
L[2031]=L[2031].replace("constraints + wideIndex","constraints - wideIndex")
open(p,"w",encoding="utf-8",newline="").write("\n".join(L))
PYEOF
sed -n 2032p src/contact_solver.c
echo "== rebuild + run (defect) =="
/usr/bin/time -p nice -n 15 $PY $D/tmo.py 300 cmake --build build -j4 > $D/box2d_build_defect.log 2>&1; echo "build rc=$?"
/usr/bin/time -p nice -n 15 $PY $D/tmo.py 120 ./build/bin/test > $D/box2d_defect.log 2>&1; echo "defect run rc=$?"
echo "--- defect run output (fail lines / tail) ---"
grep -n -i "fail\|condition false\|error\|abort\|segmentation" $D/box2d_defect.log | head -20; tail -5 $D/box2d_defect.log
echo "== what COracle.check() would harvest as 'why' =="
$PY - <<'PYEOF'
import sys; sys.path.insert(0,"/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import _fail_names, _ANSI
D="/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/10-engine-refuted-harvest"
out=open(D+"/box2d_defect.log",errors="replace").read()
clean=_ANSI.sub("",out)
bad=_fail_names(clean)
print("fail names parsed:", bad)
if bad:
    print("harvest why =", repr(f"{len(bad)} test(s) failed, first: {bad[0]}"[:200]))
else:
    why=next((l.strip() for l in clean.splitlines() if "fail" in l.lower()),"suite red")
    print("harvest why =", repr(why[:200]))
PYEOF
echo "== restore =="
cp $D/contact_solver.c.orig src/contact_solver.c && sed -n 2032p src/contact_solver.c
