#!/bin/sh
# timeout.sh SECONDS cmd args...  -- GNU `timeout` is absent on this Mac; perl alarm emulates it.
secs="$1"; shift
exec perl -e 'my $t=shift; my $pid=fork; if(!$pid){exec @ARGV or die} local $SIG{ALRM}=sub{kill "TERM",$pid; sleep 2; kill "KILL",$pid; print STDERR "timeout.sh: killed after ${t}s\n"; exit 124}; alarm $t; waitpid $pid,0; exit($?>>8)' "$secs" "$@"
