#!/bin/sh
# nice + perl-alarm timeout wrapper (this machine has no coreutils `timeout`)
# usage: ./nt.sh SECONDS command args...
S="$1"; shift
exec nice -n 15 perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  die "fork failed" unless defined $pid;
  if ($pid == 0) { exec @ARGV or die "exec failed: $!"; }
  $SIG{ALRM} = sub { kill "TERM", $pid; sleep 2; kill "KILL", $pid; waitpid($pid,0); print STDERR "TIMEOUT after $s s\n"; exit 124; };
  alarm $s;
  waitpid($pid, 0);
  my $rc = $? >> 8;
  alarm 0;
  exit $rc;
' "$S" "$@"
