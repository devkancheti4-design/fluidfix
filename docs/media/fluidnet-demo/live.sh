#!/bin/zsh
# The same scenes as the recording, run live in a terminal. usage: live.sh <demo-repo-built-by-setup.sh>
ROOT="$1"; cd "$ROOT" || exit 1
export PATH=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin:$PATH
B=$'\e[1m'; C=$'\e[36m'; Y=$'\e[33m'; R=$'\e[0m'
say(){ echo; echo "${Y}${B}== $1${R}"; sleep 1.2; }
run(){ echo "${C}\$ $*${R}"; eval "$@"; LAST=$?; sleep 1.6; }
clear
say "1  the deciders are six integer laws, re-proved on this machine — no model anywhere"
run fluidfix --version
run fluidfix selfcheck
say "2  a repo it has never seen; a teammate shipped a regression"
run git log --oneline
run "git show HEAD | tail -6"
run pytest -q --tb=no
say "3  a shipped class: repaired with zero teaching, judged by the repo's own suite"
run fluidfix guard . --commit
run git log --oneline
run pytest -q --tb=no
say "4  a shape it was never taught: refused, tree byte-identical, every attempt on record"
run "sed -i '' 's/return sum(self.entries)/return max(self.entries)/' ledgerly/ledger.py && git commit -qam 'ledger: total via max' && git show HEAD | tail -4"
run pytest -q --tb=no
run fluidfix guard . --commit
echo "exit=$LAST"; sleep 1
run git status --short
run "python3 -m json.tool .fluidfix/last_refusal.json | head -14"
run "git revert --no-edit HEAD >/dev/null && git log --oneline | head -3"
say "5  teaching: a class is a signal, a rewrite, and a PROPERTY — written once, beside the code"
run "sed -n '7,33p' rules.py"
run "sed -n '35,49p' rules.py"
say "6  the taught class repairs, judged by the suite"
run "sed -i '' 's/return ledger.last()/return ledger.first()/' ledgerly/balance.py && git commit -qam 'balance: simplify closing' && pytest -q --tb=no"
run fluidfix guard . --commit --dictionary rules.py
run "git log --oneline | head -3"
say "7  same class, a different file, a position never shown to it: free"
run "sed -i '' 's/over {ledger.size()}/over {ledger.total()}/' ledgerly/report.py && git commit -qam 'report: count via total' && pytest -q --tb=no"
run fluidfix guard . --commit --dictionary rules.py
say "8  the proof. a weak suite and a naive class: the WRONG fix goes green"
run "sed -i '' 's/int(k \* (len(text) - 1))/int(k * len(text))/' ledgerly/text.py && git commit -qam 'text: simplify cut' && pytest -q --tb=no"
run cat tests/test_text.py
run fluidfix guard . --dry-run --dictionary rules_naive.py
run "python3 -c \"t='abcdef'; k=2; print('k=2  proposed', int(k*len(t)-1), '  correct', int(k*(len(t)-1)))\""
say "9  teach the PROPERTY: what every rewrite must keep true, for every length, before any test"
cat >> rules_naive.py <<'PY'

def placement_preserves_value(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    intended = re.sub(r"\blen\(\w+\)", "(__L - 1)", o, count=1)
    actual = re.sub(r"\blen\(\w+\)", "__L", c, count=1)
    return propcheck.agree_over(intended, actual, grid=(1, 2, 3, 5, 8))

teach_property(7, "the candidate equals the original with len(x) -> (len(x) - 1), for every length",
               placement_preserves_value)
PY
run "tail -9 rules_naive.py"
run fluidfix guard . --commit --dictionary rules_naive.py
echo "exit=$LAST"; sleep 1
run git status --short
run "python3 -m json.tool .fluidfix/last_refusal.json | grep -B1 -A1 property"
say "10 the law decides where the token goes; the property proves it; the suite accepts it"
run fluidfix guard . --commit --dictionary rules.py
run "git log --oneline | head -2"
run pytest -q --tb=no
say "11 the vocabulary now"
run "fluidfix kinds --dictionary rules.py | grep -E '^ +[0-9]+ '"
echo; echo "${B}done — every run above happened live, judged by this repo's own tests.${R}"
