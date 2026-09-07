#!/bin/sh
# timeout wrapper: t.sh SECONDS cmd args...   (no coreutils timeout on this box)
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or exit 127; }
  $SIG{ALRM} = sub { kill(-9, $pid); waitpid($pid,0); print STDERR "\n[TIMEOUT after ${s}s]\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $?;
  alarm 0;
  exit($rc >> 8);
' "$S" "$@"
