#!/bin/sh
# timeout wrapper: no coreutils `timeout` on this machine.
# usage: ./tmo.sh SECONDS cmd args...
S="$1"; shift
exec nice -n 15 perl -e '
  my $t = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill "KILL", -$pid; kill "KILL", $pid; print STDERR "\n[tmo] TIMEOUT after ${t}s\n"; exit 124; };
  alarm $t;
  waitpid($pid, 0);
  alarm 0;
  exit($? >> 8);
' "$S" "$@"
