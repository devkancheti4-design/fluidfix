#!/bin/sh
# A legitimate --python: logs every invocation, then execs the real interpreter.
# Counts the SUITE RUNS estimate's arithmetic is denominated in. fluidfix is
# not modified in any way.
echo "$(date +%s.%N) $*" >> "${FLUIDFIX_SHIM_LOG:-/dev/null}"
exec /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python "$@"
