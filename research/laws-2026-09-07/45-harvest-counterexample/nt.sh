#!/bin/sh
# nice + timeout wrapper (this machine has no coreutils `timeout`).
# usage: ./nt.sh SECONDS command [args...]
# exits 124 on timeout, otherwise the child's exit status.
S="$1"; shift
exec nice -n 15 perl -e '
my $t = shift @ARGV;
my $pid = fork();
die "fork failed: $!" unless defined $pid;
if ($pid == 0) { exec @ARGV or die "exec failed: $!"; }
$SIG{ALRM} = sub { kill 9, $pid; waitpid $pid, 0; exit 124 };
alarm $t;
waitpid $pid, 0;
my $rc = $?;
alarm 0;
exit($rc & 127 ? 128 + ($rc & 127) : $rc >> 8);
' "$S" "$@"
