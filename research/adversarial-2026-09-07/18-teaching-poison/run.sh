#!/bin/zsh
# timeout wrapper: this machine has no coreutils `timeout`.
# usage: ./run.sh SECONDS cmd args...
# nice -n 15, hard wall-clock via perl alarm, kills the whole process group.
SECS=$1; shift
exec nice -n 15 perl -e '
  my $t = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill(9, -$pid); waitpid($pid,0); print STDERR "\n[TIMEOUT ${t}s]\n"; exit 124; };
  alarm $t;
  waitpid($pid, 0);
  my $rc = $? >> 8;
  alarm 0;
  exit $rc;
' "$SECS" "$@"
