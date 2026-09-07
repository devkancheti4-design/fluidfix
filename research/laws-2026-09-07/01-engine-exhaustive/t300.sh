#!/bin/sh
# `timeout 300` equivalent: macOS here has no coreutils `timeout`.
# Prefers gtimeout; else a perl alarm(300) that survives exec (POSIX: alarm timers persist across exec).
if command -v gtimeout >/dev/null 2>&1; then exec gtimeout 300 "$@"; fi
exec perl -e 'alarm 300; exec @ARGV or die "exec: $!"' -- "$@"
