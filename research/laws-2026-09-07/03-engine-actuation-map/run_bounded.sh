#!/bin/sh
# The brief asks for `nice -n 15` + `timeout 300`. This Mac has neither
# `timeout` nor `gtimeout` (checked: command -v timeout gtimeout -> nothing),
# so the 300 s bound is implemented with perl's alarm(). Same effect:
# SIGALRM kills the child after 300 s.
exec nice -n 15 perl -e 'alarm 300; exec @ARGV' "$@"
