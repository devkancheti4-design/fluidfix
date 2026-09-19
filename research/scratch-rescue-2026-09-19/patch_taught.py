"""Correct taught.html against what the 2026-09-19 measurements actually found.

The page ends by asking for one thing — point it at a real repository — and that ran the next day. The
answer contradicts two of the page's claims, so the page has to say so rather than stay pretty.
"""
from pathlib import Path

p = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
         "c9d45c92-f62a-4175-9720-836fc6f3aa9d/scratchpad/ghp/taught.html")
s = p.read_text()

# ---------------------------------------------------------------- 1. a correction notice, up front
old_lede_end = '</header>\n\n<hr>'
new_lede_end = '''  <div style="margin-top:1.6em;background:#F6E9E2;border:1px solid #EBD6C9;border-left:3px solid #B4532A;
              border-radius:8px;padding:1em 1.15em">
    <h3 style="color:#B4532A;margin:0 0 .35em">Corrected 19 September 2026 — read this first</h3>
    <p style="margin:0;font-size:.92rem;color:#6B4230">This page asked for one thing: point it at real
    repositories. That ran the next day, and it contradicts two claims below. <strong>On 57 real bug fixes
    that ship their own regression test, the vocabulary produced 0 correct repairs and 2 wrong ones.</strong>
    And the 100% on generated bugs was measured on instances that varied names but never the syntactic
    position of the fault — varying that exposes a form where one of these four classes is wrong every time.
    Both sections are annotated below rather than deleted.</p>
  </div>
</header>

<hr>'''
assert old_lede_end in s
s = s.replace(old_lede_end, new_lede_end, 1)

# ---------------------------------------------------------------- 2. the generalisation caveat
old_box = '''    <div class="box"><div class="k good">0 → 30</div><div class="t">out of 30, per class</div>
      <p>Each class took its <em>entire</em> share of the stream the moment it was loaded — not a
      diminishing fraction. A shape does not wear out on inputs it has not seen.</p></div>'''
new_box = '''    <div class="box"><div class="k good">0 → 30</div><div class="t">out of 30, per class</div>
      <p>Each class took its <em>entire</em> share of the stream the moment it was loaded — not a
      diminishing fraction. A shape does not wear out on inputs it has not seen.</p>
      <p style="color:#B4532A"><strong>Corrected:</strong> those instances varied names, values and
      surrounding code, but never the <em>syntactic position</em> of the fault. They were all of the form
      the class was taught on.</p></div>'''
assert old_box in s
s = s.replace(old_box, new_box, 1)

# insert the position-varying table right after the two boxes
anchor = '''  <p style="margin-top:1.3em">Two of those four classes were written the same afternoon'''
pos_table = '''  <div class="callout" style="margin-top:1.4em">
    <h3>What varying the position shows</h3>
    <p>Same class — <code>len-as-last-index</code> — same judge, same discipline, but now the
    <em>position</em> of <code>len(...)</code> varies instead of only the names:</p>
    <div class="tablewrap" style="margin-top:.8em">
      <table>
        <thead><tr><th>the shape of the line</th><th class="r">repaired</th></tr></thead>
        <tbody>
          <tr><td><code>last = len(x)</code> — the shape it was taught on</td><td class="r good">12/12</td></tr>
          <tr><td><code>off + len(x)</code></td><td class="r good">12/12</td></tr>
          <tr><td><code>min(99, len(x))</code></td><td class="r good">12/12</td></tr>
          <tr><td><code>k * len(x)</code></td><td class="r" style="color:#B4532A"><strong>0/12</strong></td></tr>
        </tbody>
      </table>
    </div>
    <p style="margin-top:.8em">The applier appends <code>- 1</code> after the closing paren. That is right
    where <code>len(...)</code> is the whole right-hand side, right under <code>+</code> by associativity,
    right inside a call — and <strong>wrong under any operator that binds tighter than <code>-</code></strong>.
    The class generalised its <em>signal</em> but not its <em>semantics</em>, and on <code>rich</code> that
    shipped a wrong repair that the project's own tests accepted.</p>
  </div>

''' + anchor
assert anchor in s
s = s.replace(anchor, pos_table, 1)

# ---------------------------------------------------------------- 3. replace the closing ask with the answer
start = s.index('<!-- ============ THE OPEN QUESTION ============ -->')
end = s.index('<footer class="wrap">')
answered = '''<!-- ============ THE ANSWER ============ -->
<section class="wrap">
  <p class="eyebrow">the measurement this page asked for</p>
  <h2>We scanned real repositories. The answer is 0.</h2>
  <p>This page used to end by asking for a real codebase instead of a corpus we built. That ran on
  19 September: 9,927 commits across click, arrow, rich and python-sortedcontainers, filtered to fixes that
  change one source file <em>and ship their own regression test</em> — because that test is a judge nobody
  can argue with.</p>

  <p>For each one: check out the parent commit, take only the test files from the fix, confirm the suite
  goes red, hand the source file to the vocabulary, and let the maintainer's own test decide. Nothing is
  compared to what the maintainer typed.</p>

  <div class="tablewrap">
    <table>
      <thead><tr><th>repository</th><th class="r">judged</th><th class="r">shipped</th><th class="r">correct</th></tr></thead>
      <tbody>
        <tr><td>click</td><td class="r">26</td><td class="r">0</td><td class="r">—</td></tr>
        <tr><td>python-sortedcontainers</td><td class="r">2</td><td class="r">0</td><td class="r">—</td></tr>
        <tr><td>rich</td><td class="r">29</td><td class="r">2</td><td class="r" style="color:#B4532A"><strong>0</strong></td></tr>
        <tr><td><strong>total</strong></td><td class="r"><strong>57</strong></td><td class="r"><strong>2</strong></td><td class="r" style="color:#B4532A"><strong>0</strong></td></tr>
      </tbody>
    </table>
  </div>

  <div class="callout">
    <h3>Two repairs shipped. Both were wrong.</h3>
    <p><code>rich/segment.py</code> — the <code>- 1</code> went outside the multiplication instead of
    inside it. Over 1,452 input combinations the two forms disagree on 736.</p>
    <p><code>rich/traceback.py</code> — it changed a padding tuple 135 lines from the actual fault. A
    compensating edit, not a repair.</p>
    <p>Both pass all six certification gates. Both slipped through partly because 22 and 24 tests were
    already failing under a modern interpreter and had to be set aside for the experiment to run at all —
    the tool is exactly as good as the suite it is given, and thinning the suite by about 4% was enough.</p>
  </div>

  <h3 style="margin-top:1.8em">Why, and it is not about which shapes are taught</h3>
  <p>Only <strong>11 of the 57</strong> judged fixes were one-line diffs at all. A vocabulary that rewrites
  one line cannot express the other 46 however much is taught. The seeded mutations behind our earlier
  figures were single-line <em>by construction</em>, and that is the whole of the difference. <strong>Real
  bug fixes are mostly not single-line edits.</strong></p>

  <h3 style="margin-top:1.6em">What survives</h3>
  <p>The <strong>localisation</strong>, which was never on trial. All 57 cases named the file, ranked the
  lines the failing test executed, and printed the test that killed each candidate — at zero tokens. And a
  model asked to review the two wrong patches, one at a time with no rival beside it, rejected both — while
  also rejecting one of the two correct fixes. A second judge in series can only tighten; on four cases it
  removed 2 of 2 bad patches and cost 1 of 2 good ones.</p>
</section>

<hr>

'''
s = s[:start] + answered + s[end:]

p.write_text(s)
print(f"patched taught.html — {len(s)} bytes")
