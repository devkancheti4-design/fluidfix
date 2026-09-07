#!/bin/sh
# run.sh SECONDS CMD... -- nice + perl-alarm timeout (no coreutils `timeout` here)
# exits 124 on timeout, like GNU timeout.
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or exit 127; }
  $SIG{ALRM} = sub { kill(-9, $pid); waitpid($pid,0); exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $?;
  alarm 0;
  exit($rc >> 8 ? $rc >> 8 : ($rc & 127 ? 128 + ($rc & 127) : 0));
' "$S" "$@"
