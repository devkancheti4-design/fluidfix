#!/bin/sh
# 300 s wall-clock wrapper (macOS ships no `timeout`); niced as the brief asks.
exec perl -e 'alarm 300; exec @ARGV' nice -n 15 "$@"
