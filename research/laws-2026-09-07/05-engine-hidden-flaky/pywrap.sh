#!/bin/sh
# Logs every interpreter invocation fluidfix makes (one line per call) to
# $FLUIDFIX_PYLOG, then runs the real venv python. Passed as --python so the
# number of pytest runs per repair can be counted from outside the process.
printf '%s\n' "$*" >> "$FLUIDFIX_PYLOG"
exec /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python "$@"
