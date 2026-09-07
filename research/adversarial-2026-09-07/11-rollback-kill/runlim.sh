#!/bin/bash
# runlim.sh SECS CMD...   nice -n 15 + perl-alarm hard timeout (no coreutils timeout here).
# Child inherits THIS process group so a killpg from the launcher reaches the whole tree.
# On its own alarm, SIGKILLs the child. Exit 124 on timeout.
secs="$1"; shift
exec nice -n 15 perl -e '
  my $t = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { exec @ARGV or exit 127; }
  $SIG{ALRM} = sub { kill("KILL", $pid); waitpid($pid,0); exit 124; };
  alarm $t;
  waitpid($pid, 0);
  my $rc = $?;
  exit( ($rc & 127) ? 128 + ($rc & 127) : ($rc >> 8) );
' "$secs" "$@"
