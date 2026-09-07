#!/bin/sh
# timeout wrapper: this machine has no coreutils `timeout`.
# usage: run.sh <seconds> <cmd> [args...]
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork failed" unless defined $pid;
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or exit 127; }
  $SIG{ALRM} = sub { kill "KILL", -$pid; waitpid($pid, 0); print STDERR "\n[[TIMEOUT after ${s}s]]\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $? >> 8;
  alarm 0;
  exit $rc;
' "$S" "$@"
