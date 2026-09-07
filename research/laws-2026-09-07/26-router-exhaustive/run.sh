#!/bin/sh
# Timeout wrapper: this machine has no coreutils `timeout`.
# Usage: ./run.sh <seconds> <command...>
# Runs the command at nice -n 15 under a perl alarm of <seconds>.
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork failed" unless defined $pid;
  if ($pid == 0) { exec @ARGV or exit 127; }
  $SIG{ALRM} = sub { kill "KILL", $pid; waitpid($pid,0); print STDERR "TIMEOUT after ${s}s\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  alarm 0;
  exit($? >> 8);
' "$S" "$@"
