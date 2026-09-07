#!/bin/sh
OUT="$1"; : > "$OUT"
i=0
while [ $i -lt 100 ]; do
  N=$(ps -axo command= | grep -c 'FFX14MARKER-service' )
  echo "$(date +%H:%M:%S) leaked_or_live_services=$((N-1))" >> "$OUT"
  i=$((i+1)); sleep 2
done
