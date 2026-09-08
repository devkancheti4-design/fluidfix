# neo — an unseen repo, a real terminal, the real tool. Every command runs
# live while recording; nothing is generated.
Output neo-teach.mp4
Set Shell zsh
Set Width 1920
Set Height 1080
Set FontSize 32
Set LineHeight 1.25
Set Padding 44
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms
Set CursorBlink false

Hide
Type "cd /Users/kanchetidevieswar/neo/demo/shipwise && export PATH=/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH && clear" Enter
Sleep 1s
Show

# 1 - the laws, re-proved on this machine
Type "fluidfix --version" Enter
Sleep 1.5s
Type "fluidfix selfcheck" Enter
Sleep 4s
Ctrl+L

# 2 - an unseen repo; a teammate shipped a regression
Type "git log --oneline" Enter
Sleep 2s
Type "git show HEAD" Enter
Sleep 5s
Type "pytest -q --tb=no" Enter
Sleep 3.5s
Ctrl+L

# 3 - a shipped class: repaired with zero teaching, zero tokens
Type "fluidfix guard . --commit" Enter
Sleep 6s
Type "git log --oneline" Enter
Sleep 3s
Type "pytest -q --tb=no" Enter
Sleep 3s
Ctrl+L

# 4 - a class it has never seen: refused, tree untouched
Type "sed -i '' 's/round(total, 2)/round(total)/' shipwise/quote.py && git commit -qam 'quote: simplify rounding' && git show HEAD" Enter
Sleep 4s
Type "pytest -q --tb=no" Enter
Sleep 3s
Type "fluidfix guard . --commit" Enter
Sleep 12s
Type "echo exit=$?" Enter
Sleep 1.5s
Type "git status --short" Enter
Sleep 2.5s
Type "python3 -m json.tool .fluidfix/last_refusal.json | head -16" Enter
Sleep 6s
Ctrl+L

# 5 - teach it: ONE structured example
Set TypingSpeed 22ms
Type `cat > rules.py <<'EOF'` Enter
Type `# neo learns from STRUCTURED examples, never from prose.` Enter
Type `# one worked example = line before, line after, a signal, a transform` Enter
Type `#` Enter
Type `#   return round(total)        <- money rounded to whole units` Enter
Type `#   return round(total, 2)     <- the fix` Enter
Type `register(` Enter
Type `    4,                                      # kind: 4-7 are yours` Enter
Type `    "round-lost-precision",                 # name` Enter
Type `    'a round() on a money value with no ndigits, dropping the cents',` Enter
Type `    re.compile(r"round\(\w+\)"),            # signal: a line that can show it` Enter
Type `    lambda line, o: re.sub(r"round\((\w+)\)", r"round(\1, 2)", line),` Enter
Type `)` Enter
Type `EOF` Enter
Set TypingSpeed 45ms
Sleep 3s
Ctrl+L

# 6 - the class repairs itself, judged by the repo's own tests
Type "fluidfix guard . --commit --dictionary rules.py" Enter
Sleep 8s
Type "git log --oneline" Enter
Sleep 3s
Ctrl+L

# 7 - same class, another file: free
Type "sed -i '' 's/round(gross, 2)/round(gross)/' shipwise/invoice.py && git commit -qam 'invoice: simplify rounding' && pytest -q --tb=no" Enter
Sleep 4s
Type "fluidfix guard . --commit --dictionary rules.py" Enter
Sleep 8s
Type "git log --oneline" Enter
Sleep 4s
Ctrl+L

# 8 - the vocabulary now: shipped classes plus the one just taught
Type "fluidfix kinds --dictionary rules.py | grep -E '^ +[0-9]+ '" Enter
Sleep 7s
