#!/bin/zsh
# timeout wrapper: no coreutils `timeout` on this host. usage: run.sh SECS cmd...
S=$1; shift
exec nice -n 15 /usr/bin/perl -e '
  my $s = shift @ARGV;
  my $pid = fork();
  if ($pid == 0) { setpgrp(0,0); exec @ARGV or die "exec: $!"; }
  $SIG{ALRM} = sub { kill(-9, $pid); waitpid($pid, 0); print STDERR "\n[TIMEOUT ${s}s]\n"; exit 124; };
  alarm($s);
  waitpid($pid, 0);
  my $rc = $? >> 8;
  alarm(0);
  exit $rc;
' "$S" "$@"
