#!/bin/sh
# timeout wrapper: this machine has no coreutils `timeout`.
# usage: ./run.sh SECONDS command...
# Runs the command under `nice -n 15` with a perl alarm that kills the child.
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { setpgrp(0,0); exec @ARGV; exit 127; }
  $SIG{ALRM} = sub { kill(-9, $pid); waitpid($pid,0); print STDERR "\n[[TIMEOUT after ${s}s]]\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $?; alarm 0;
  exit($rc >> 8);
' "$S" "$@"
