#!/bin/sh
# Portable stand-in for `nice -n 15 timeout <secs> <cmd...>`.
# This machine has no GNU coreutils `timeout` (verified: `which timeout gtimeout`
# -> "not found"), so the brief's hard limit is enforced with perl's alarm,
# which sends SIGALRM to the exec'd child after <secs> seconds.
# Usage:  ./run.sh <secs> <command> [args...]
secs="$1"; shift
exec nice -n 15 perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$secs" "$@"
