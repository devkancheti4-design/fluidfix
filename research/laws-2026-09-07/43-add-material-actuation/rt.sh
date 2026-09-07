#!/bin/sh
# rt.sh SECONDS CMD...  -- this machine has no coreutils `timeout`.
# nice -n 15 + a perl alarm wrapper. Exit 124 on timeout (timeout(1) convention).
secs="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill "TERM", $pid; sleep 2; kill "KILL", $pid; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $?;
  exit($rc & 127 ? 128 + ($rc & 127) : $rc >> 8);
' "$secs" "$@"
