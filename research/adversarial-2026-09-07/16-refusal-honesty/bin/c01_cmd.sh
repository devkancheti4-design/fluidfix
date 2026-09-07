#!/bin/sh
# reproduce: c01_frame, the failure prints two SOURCE frames
D="$(cd "$(dirname "$0")/.." && pwd)"
cd "$D/fixtures/c/c01_frame"
cp "$D/pristine/c01_mathops.c" src/mathops.c; touch src/mathops.c
BC='cc -O0 -o build/tests src/mathops.c src/util.c tests/test_main.c'
exec "$D/bin/run" 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix cguard . \
     --build-cmd "$BC" --test-cmd ./build/tests "$@"
