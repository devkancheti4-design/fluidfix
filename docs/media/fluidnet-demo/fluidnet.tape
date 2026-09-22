# fluidnet — a real repo, a real terminal, the real tool. Every command runs live while
# recording; nothing is generated. setup.sh rebuilds the starting state.
Output fluidnet.mp4
Set Shell zsh
Set Width 1920
Set Height 1080
Set FontSize 28
Set LineHeight 1.25
Set Padding 44
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set CursorBlink false

Hide
Type "cd /Users/kanchetidevieswar/neo/demo/ledgerly && export PATH=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin:$PATH && clear" Enter
Sleep 1s
Show

# 1 - the deciders are six integer laws, re-proved on this machine, no model anywhere
Type "fluidfix --version" Enter
Sleep 1.5s
Type "fluidfix selfcheck" Enter
Sleep 5s
Ctrl+L

# 2 - a repo it has never seen; a teammate shipped a regression
Type "git log --oneline" Enter
Sleep 2s
Type "git show HEAD | tail -6" Enter
Sleep 4s
Type "pytest -q --tb=no" Enter
Sleep 3s
Ctrl+L

# 3 - a shipped class: repaired with zero teaching, zero tokens, judged by the repo's own suite
Type "fluidfix guard . --commit" Enter
Sleep 6s
Type "git log --oneline" Enter
Sleep 2.5s
Type "pytest -q --tb=no" Enter
Sleep 3s
Ctrl+L

# 4 - a shape it was never taught: refused, tree byte-identical, every attempt on record
Type "sed -i '' 's/return sum(self.entries)/return max(self.entries)/' ledgerly/ledger.py && git commit -qam 'ledger: total via max' && git show HEAD | tail -4" Enter
Sleep 4s
Type "pytest -q --tb=no" Enter
Sleep 3s
Type "fluidfix guard . --commit" Enter
Sleep 8s
Type "echo exit=$?" Enter
Sleep 1.5s
Type "git status --short" Enter
Sleep 2.5s
Type "python3 -m json.tool .fluidfix/last_refusal.json | head -14" Enter
Sleep 6s
Type "git revert --no-edit HEAD >/dev/null && git log --oneline | head -3" Enter
Sleep 3s
Ctrl+L

# 5 - teaching: a class is a signal, a rewrite, and a PROPERTY. written once, beside the code
Type "sed -n '7,20p' rules.py" Enter
Sleep 8s
Ctrl+L
Type "sed -n '22,33p' rules.py" Enter
Sleep 7s
Ctrl+L
Type "sed -n '35,49p' rules.py" Enter
Sleep 8s
Ctrl+L

# 6 - the taught class repairs, judged by the suite
Type "sed -i '' 's/return ledger.last()/return ledger.first()/' ledgerly/balance.py && git commit -qam 'balance: simplify closing' && pytest -q --tb=no" Enter
Sleep 4s
Type "fluidfix guard . --commit --dictionary rules.py" Enter
Sleep 6s
Type "git log --oneline | head -3" Enter
Sleep 3s
Ctrl+L

# 7 - same class, a different file, a position never shown to it: free
Type "sed -i '' 's/over {ledger.size()}/over {ledger.total()}/' ledgerly/report.py && git commit -qam 'report: count via total' && pytest -q --tb=no" Enter
Sleep 4s
Type "fluidfix guard . --commit --dictionary rules.py" Enter
Sleep 6s
Ctrl+L

# 8 - the proof. a weak suite, a naive class: the WRONG fix goes green
Type "sed -i '' 's/int(k \* (len(text) - 1))/int(k * len(text))/' ledgerly/text.py && git commit -qam 'text: simplify cut' && pytest -q --tb=no" Enter
Sleep 4s
Type "cat tests/test_text.py" Enter
Sleep 5s
Type "fluidfix guard . --dry-run --dictionary rules_naive.py" Enter
Sleep 8s
Type `python3 -c "t='abcdef'; k=2; print('k=2  proposed', int(k*len(t)-1), '  correct', int(k*(len(t)-1)))"` Enter
Sleep 5s
Ctrl+L

# 9 - teach the PROPERTY: what every rewrite must keep true, checked for every length, before any test
Set TypingSpeed 22ms
Type `cat >> rules_naive.py <<'EOF'` Enter
Type `def placement_preserves_value(orig, cand):` Enter
Type `    o, c = propcheck.rhs(orig), propcheck.rhs(cand)` Enter
Type `    intended = re.sub(r"\blen\(\w+\)", "(__L - 1)", o, count=1)` Enter
Type `    actual = re.sub(r"\blen\(\w+\)", "__L", c, count=1)` Enter
Type `    return propcheck.agree_over(intended, actual, grid=(1, 2, 3, 5, 8))` Enter
Type `teach_property(7, "the candidate equals the original with len(x) -> (len(x) - 1), for every length",` Enter
Type `               placement_preserves_value)` Enter
Type `EOF` Enter
Set TypingSpeed 40ms
Sleep 2s
Type "fluidfix guard . --commit --dictionary rules_naive.py" Enter
Sleep 8s
Type "echo exit=$?" Enter
Sleep 1.5s
Type "git status --short" Enter
Sleep 2.5s
Type "python3 -m json.tool .fluidfix/last_refusal.json | grep -B1 -A1 property" Enter
Sleep 6s
Ctrl+L

# 10 - the law decides where the token goes; the property proves it; the suite accepts it
Type "fluidfix guard . --commit --dictionary rules.py" Enter
Sleep 6s
Type "git log --oneline | head -2" Enter
Sleep 3s
Type "pytest -q --tb=no" Enter
Sleep 3s
Ctrl+L

# 11 - the vocabulary now
Type "fluidfix kinds --dictionary rules.py | grep -E '^ +[0-9]+ '" Enter
Sleep 7s
