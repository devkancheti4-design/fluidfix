#!/bin/sh
# timeout(1) substitute for macOS: with_timeout.sh SECONDS cmd args...
# (BRIEF asks for `timeout 300`; there is no timeout binary on this host)
secs="$1"; shift
exec perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$secs" "$@"
