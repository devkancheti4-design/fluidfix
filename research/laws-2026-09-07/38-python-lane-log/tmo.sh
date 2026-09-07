#!/bin/sh
# timeout wrapper: this machine has no coreutils `timeout`.
# usage: tmo.sh SECONDS cmd args...
# Runs the command under `nice -n 15` and kills it after SECONDS via a perl alarm.
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork: $!" unless defined $pid;
  if ($pid == 0) { exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill "TERM", $pid; sleep 3; kill "KILL", $pid;
                     print STDERR "\n[tmo] TIMEOUT after ${s}s\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  alarm 0;
  exit($? >> 8);
' "$S" "$@"
