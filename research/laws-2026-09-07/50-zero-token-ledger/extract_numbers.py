"""Extract every numeric claim from a text or HTML file, with line/context.
Usage: python extract_numbers.py FILE [--html]
"""
import re, sys, html as htmlmod

path = sys.argv[1]
is_html = path.endswith(".html")
raw = open(path, encoding="utf-8", errors="replace").read()
if is_html:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S|re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S|re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = htmlmod.unescape(raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    # split into sentence-ish chunks
    lines = [l.strip() for l in re.split(r"\n", raw)]
else:
    lines = raw.split("\n")

NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
out = []
for i, line in enumerate(lines, 1):
    if not line.strip():
        continue
    for m in NUM.finditer(line):
        out.append((i, m.group(0), line.strip()))
seen = set()
for i, n, ctx in out:
    key = (n, ctx)
    if key in seen:
        continue
    seen.add(key)
    print(f"{i}\t{n}\t{ctx[:200]}")
