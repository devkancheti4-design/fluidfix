#!/bin/sh
# reproduce: c02_capped_green — a green is found, then the budget cuts the search
D="$(cd "$(dirname "$0")/.." && pwd)"
cd "$D/fixtures/c/c02_capped_green"
cp "$D/pristine/c02_mathops.c" src/mathops.c; touch src/mathops.c
BC='cc -O0 -o build/tests src/mathops.c tests/test_main.c'
exec "$D/bin/run" 600 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix cguard . \
     --build-cmd "$BC" --test-cmd ./build/tests "$@"
