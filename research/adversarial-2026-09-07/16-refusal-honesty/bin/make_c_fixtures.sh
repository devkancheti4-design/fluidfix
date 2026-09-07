#!/bin/sh
set -e
D="$(cd "$(dirname "$0")/.." && pwd)"
F="$D/fixtures/c"
rm -rf "$F"; mkdir -p "$F"

# ---- c01_frame: the failing test PRINTS a source frame  src/mathops.c:LINE:
mkdir -p "$F/c01_frame/src" "$F/c01_frame/tests" "$F/c01_frame/build"
cat > "$F/c01_frame/src/mathops.c" <<'EOF'
int addv(int a, int b)
{
    return a - b;
}
EOF
cat > "$F/c01_frame/tests/test_main.c" <<'EOF'
#include <stdio.h>
int addv(int a, int b);
int main(void)
{
    int r = addv(2, 3);
    if (r != 5) {
        printf("src/mathops.c:3: assertion failed: addv(2,3) == 5 (got %d)\n", r);
        printf("test failed: MathopsTest\n");
        return 1;
    }
    printf("all tests passed\n");
    return 0;
}
EOF

# ---- c02_capped_green: same defect, plus padding lines so the search has
#      plenty left to do AFTER the green is found.
mkdir -p "$F/c02_capped_green/src" "$F/c02_capped_green/tests" "$F/c02_capped_green/build"
/usr/bin/python3 - "$F/c02_capped_green/src/mathops.c" <<'EOF'
import sys
L = ["int addv(int a, int b)", "{", "    int r = a - b;"]
for i in range(1, 16):
    L.append(f"    int pad{i} = {i} * 2 + {i};")
L.append("    (void)(" + " + ".join(f"pad{i}" for i in range(1, 16)) + ");")
L.append("    return r;")
L.append("}")
open(sys.argv[1], "w").write("\n".join(L) + "\n")
EOF
cp "$F/c01_frame/tests/test_main.c" "$F/c02_capped_green/tests/test_main.c"

# ---- c03_outofvocab: a genuine out-of-vocabulary defect (wrong function body)
mkdir -p "$F/c03_outofvocab/src" "$F/c03_outofvocab/tests" "$F/c03_outofvocab/build"
cat > "$F/c03_outofvocab/src/mathops.c" <<'EOF'
int addv(int a, int b)
{
    return a * b;
}
EOF
cat > "$F/c03_outofvocab/tests/test_main.c" <<'EOF'
#include <stdio.h>
int addv(int a, int b);
int main(void)
{
    if (addv(2, 3) != 5 || addv(4, 4) != 8) {
        printf("src/mathops.c:3: assertion failed\n");
        printf("test failed: MathopsTest\n");
        return 1;
    }
    printf("all tests passed\n");
    return 0;
}
EOF

for r in "$F"/*; do
  mkdir -p "$r/build"
  ( cd "$r" && cc -O0 -o build/tests src/mathops.c tests/test_main.c )
done
echo built: ; ls "$F"
