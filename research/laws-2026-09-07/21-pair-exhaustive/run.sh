#!/bin/sh
# This macOS box has no coreutils `timeout` (verified: `which timeout gtimeout`
# -> not found). Same contract: nice -n 15, hard 300s wall-clock kill.
exec nice -n 15 perl -e 'alarm shift @ARGV; exec @ARGV or die $!' 300 "$@"
