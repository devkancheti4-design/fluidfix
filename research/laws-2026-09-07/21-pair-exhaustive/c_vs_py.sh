#!/bin/sh
# Compare the authored C kernel (docs/laws/pair.c) with the vendored Python
# port on all 256 inputs, and run the authored self-check unmodified.
set -e
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/21-pair-exhaustive
R=/Users/kanchetidevieswar/neo/fluidfix
cp "$R/docs/laws/pair.c" "$D/pair_copy.c"
sed 's/^int main(void)$/int authored_selfcheck(void)/' "$D/pair_copy.c" > "$D/pair_kernel.c"
cat > "$D/dump.c" <<'C'
#include "pair_kernel.c"
int main(void){ for (int32_t x=0;x<256;x++) printf("%d %d\n", x, pair_law(x)); return 0; }
C
"$D/run.sh" cc -O2 -o "$D/pair_dump" "$D/dump.c"
"$D/run.sh" cc -O2 -o "$D/pair_selfcheck" "$D/pair_copy.c"
"$D/run.sh" "$D/pair_dump" > "$D/c_outputs.txt"
"$R/.venv/bin/python" - <<'PY'
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.pair import pair_law
D="/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/21-pair-exhaustive"
c={}
for line in open(D+"/c_outputs.txt"):
    x,v=line.split(); c[int(x)]=int(v)
bad=[x for x in range(256) if c[x]!=pair_law(x)]
print("C kernel vs Python port, all 256 inputs: %d disagreements %s"%(len(bad),bad))
PY
echo "--- authored self-check (docs/laws/pair.c, unmodified) ---"
"$D/run.sh" "$D/pair_selfcheck"
