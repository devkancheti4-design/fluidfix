#!/bin/sh
# macOS has no coreutils `timeout`. This is the brief's "wrapped in a timeout".
# usage: ./timeout.sh SECONDS cmd args...
exec nice -n 15 perl -e 'my $t=shift; $SIG{ALRM}=sub{ kill -9, $$; exit 124 }; setpgrp(0,0); alarm $t; exec @ARGV or exit 127;' "$@"
