#!/bin/sh
# timeout wrapper: no coreutils `timeout` on this machine.
# usage: run.sh SECONDS cmd args...
S="$1"; shift
exec nice -n 15 perl -e 'my $t=shift; $SIG{ALRM}=sub{ print STDERR "TIMEOUT after $t s\n"; kill 9,-$$; exit 124 }; alarm $t; setpgrp(0,0); exec @ARGV or die "exec: $!";' "$S" "$@"
