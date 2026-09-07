#!/bin/sh
# timeout(1) substitute for macOS: tmo.sh SECONDS cmd args...
# uses gtimeout when present, else a perl alarm wrapper
if command -v gtimeout >/dev/null 2>&1; then exec gtimeout "$@"; fi
secs="$1"; shift
exec perl -e 'my $t=shift; $SIG{ALRM}=sub{kill "TERM", $pid; sleep 2; kill "KILL", $pid; exit 124}; $pid=fork; if($pid==0){exec @ARGV or exit 127} alarm $t; waitpid($pid,0); exit($? >> 8)' "$secs" "$@"
