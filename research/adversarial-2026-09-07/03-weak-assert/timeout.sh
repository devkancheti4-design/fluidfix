#!/bin/sh
# timeout wrapper: this machine has no coreutils `timeout`.
#   usage: ./timeout.sh SECONDS cmd args...
# perl alarm kills the whole process group on expiry; exit 124 on timeout.
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill(-9, $pid); waitpid($pid, 0); exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $?;
  alarm 0;
  exit($rc >> 8) if ($rc & 127) == 0;
  exit(128 + ($rc & 127));
' "$S" "$@"
