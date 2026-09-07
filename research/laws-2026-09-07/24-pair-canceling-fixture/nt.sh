#!/bin/sh
# nice + timeout wrapper (macOS has no coreutils `timeout`): nt.sh SECONDS CMD...
SECS=$1; shift
exec nice -n 15 perl -e 'alarm shift; exec @ARGV' "$SECS" "$@"
