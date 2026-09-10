#!/bin/zsh
# Maintenance-loop properties, each on its own copy of ledgerkit:
#  P1 green suite -> nothing to do, no commit
#  P2 a REAL crash: kill -9 the guard while a candidate is on disk; next run restores from the journal, then repairs
#  P3 --interval watch mode: a regression shipped while it watches is repaired on the next tick, nothing re-queued
export PATH=/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
S=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/maint
L=$S/ledgerkit-loop; rm -rf $L; python3 $M/pyrepo.py $L >/dev/null; cd $L
BASE=$(git rev-parse --short HEAD)
say(){ echo "$@" | tee -a $M/loop_props.log; }
: > $M/loop_props.log
say "== P1 green suite"
fluidfix guard . --commit 2>&1 | tee -a $M/loop_props.log; say "exit=$? commits=$(git rev-list --count HEAD) (base had 1)"

say "== P2 real crash mid-candidate"
sed -i '' 's/return net \* (1 + rate)/return net * (1 - rate)/' ledgerkit/tax.py && git commit -qam "tax: tidy formula"
fluidfix guard . --commit > $M/p2_killed.log 2>&1 & GP=$!
for i in {1..200}; do [ -f .fluidfix/inflight.json ] && break; sleep 0.05; done
kill -9 $GP 2>/dev/null; wait $GP 2>/dev/null
say "killed guard pid $GP after $((i*50))ms; journal present: $([ -f .fluidfix/inflight.json ] && echo yes || echo no); tax.py now: $(grep -o 'net \* ([^)]*)' ledgerkit/tax.py)"
say "-- next run:"; fluidfix guard . --commit 2>&1 | tee -a $M/loop_props.log; say "exit=$? journal after: $([ -f .fluidfix/inflight.json ] && echo still-there || echo removed); tax.py now: $(grep -o 'net \* ([^)]*)' ledgerkit/tax.py); log: $(git log --oneline -1)"

say "== P3 --interval watch mode (tick every 4s)"
nohup fluidfix guard . --interval 4 --commit > $M/p3_watch.log 2>&1 & WP=$!
sleep 6; say "watcher pid $WP first tick: $(tail -1 $M/p3_watch.log)"
sed -i '' 's/return max(0.0, amount)/return min(0.0, amount)/' ledgerkit/money.py && git commit -qam "money: tidy clamp" && say "shipped regression at $(date +%T): $(git log --oneline -1)"
for i in {1..30}; do grep -q "repaired line" $M/p3_watch.log && break; sleep 1; done
say "watcher log after ${i}s:"; cat $M/p3_watch.log | tee -a $M/loop_props.log
kill $WP 2>/dev/null; wait $WP 2>/dev/null
say "git log: $(git log --oneline | head -3 | tr '\n' ' | ')"; say "money.py now: $(grep -o 'return m..(0.0, amount)' ledgerkit/money.py)"
