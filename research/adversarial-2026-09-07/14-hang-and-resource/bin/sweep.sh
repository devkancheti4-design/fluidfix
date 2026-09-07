#!/bin/sh
# kill every FFX14MARKER helper this experiment could have created, then prove
# with ps that none survive.
for i in 1 2 3; do
  P=$(ps -axo pid=,command= | grep FFX14MARKER | grep -v grep | awk '{print $1}')
  [ -z "$P" ] && break
  echo "$P" | xargs kill -9 2>/dev/null
  sleep 1
done
echo "--- ps after sweep (want: nothing) ---"
ps -axo pid=,pgid=,command= | grep FFX14MARKER | grep -v grep || echo "  clean: 0 survivors"
