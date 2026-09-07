#!/bin/sh
# GNU `timeout` is not present on this macOS box (`which timeout` -> not found,
# `gtimeout` not found either), so the brief's `timeout 300` is emulated with
# perl's alarm, which is in the base system. Every run in this directory goes
# through here.
#   ./run.sh <cmd> [args...]
exec nice -n 15 perl -e 'alarm shift; exec @ARGV or die "exec: $!"' 300 "$@"
