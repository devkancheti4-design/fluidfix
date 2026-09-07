#!/bin/sh
# nice + perl-alarm timeout wrapper (this host has no coreutils `timeout`).
# usage: ./run.sh SECONDS cmd args...
S="$1"; shift
exec nice -n 15 perl -e '
  my $t = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill("KILL", -$pid); waitpid($pid,0); print STDERR "\n[run.sh] TIMEOUT after ${t}s\n"; exit 124; };
  alarm $t;
  waitpid($pid, 0);
  my $rc = $? >> 8;
  alarm 0;
  exit $rc;
' "$S" "$@"
