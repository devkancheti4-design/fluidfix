#!/bin/sh
# timeout wrapper: this machine has no coreutils `timeout`.
# usage: ./tmo.sh SECONDS cmd args...
# Runs the command under `nice -n 15` with a perl alarm; exit 124 on timeout.
secs="$1"; shift
exec perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { exec("nice", "-n", "15", @ARGV) or die "exec: $!"; }
  $SIG{ALRM} = sub { kill 9, $pid; waitpid($pid, 0); print STDERR "TIMEOUT after $s s\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  alarm 0;
  exit($? >> 8);
' "$secs" "$@"
