// fluidfix — sales deck. Problem, cost, what it does for you, proof, trust, offer.
// No mechanism: nothing about laws, bits or how teaching is implemented.
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.author = "Devieswar Kancheti"; pres.title = "fluidfix";

const C = { bg: "0B0F14", surface: "121821", raised: "171F2A", rule: "1F2A36", rule2: "2C3A4A",
            ink: "FFFFFF", text: "DDE3EA", muted: "8B95A2", dim: "5A6572", amber: "F2B441", ok: "5FB58A", bad: "D9776B" };
const SANS = "Calibri", MONO = "Courier New";
const W = 13.33, H = 7.5, M = 0.7;
let n = 0;

function base(eyebrow, notes) {
  const s = pres.addSlide(); n += 1;
  s.background = { color: C.bg };
  // brand mark + eyebrow (the one recurring element)
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 0.52, w: 0.3, h: 0.3, fill: { color: C.amber }, line: { color: C.amber }, rectRadius: 0.06 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M + 0.09, y: 0.61, w: 0.12, h: 0.12, fill: { color: C.bg }, line: { color: C.bg }, rectRadius: 0.02 });
  s.addText(eyebrow.toUpperCase(), { x: M + 0.42, y: 0.48, w: 8, h: 0.38, fontFace: MONO, fontSize: 11, color: C.amber, charSpacing: 2, margin: 0, isTextBox: true, valign: "middle" });
  s.addText("fluidfix · github.com/devkancheti4-design/fluidfix", { x: M, y: H - 0.62, w: 8, h: 0.3, fontFace: MONO, fontSize: 9, color: C.dim, margin: 0, isTextBox: true });
  s.addText(String(n), { x: W - M - 1, y: H - 0.62, w: 1, h: 0.3, fontFace: MONO, fontSize: 9, color: C.dim, align: "right", margin: 0, isTextBox: true });
  if (notes) s.addNotes(notes);
  return s;
}
function title(s, t, y = 1.05, size = 34, w = W - 2 * M) {
  s.addText(t, { x: M, y, w, h: 1.1, fontFace: SANS, fontSize: size, bold: true, color: C.ink, margin: 0, isTextBox: true, valign: "top" });
}
function body(s, t, x, y, w, h, opts = {}) {
  s.addText(t, Object.assign({ x, y, w, h, fontFace: SANS, fontSize: 15, color: C.text, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 8 }, opts));
}
function card(s, x, y, w, h, hi = false) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: C.surface }, line: { color: hi ? C.amber : C.rule, width: hi ? 1.5 : 1 }, rectRadius: 0.14 });
}
function stat(s, x, y, w, h, num, label, src) {
  card(s, x, y, w, h);
  s.addText(num, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.75, fontFace: MONO, fontSize: 30, bold: true, color: C.amber, margin: 0, isTextBox: true, valign: "middle" });
  s.addText(label, { x: x + 0.25, y: y + 0.95, w: w - 0.5, h: 0.6, fontFace: SANS, fontSize: 13, color: C.text, margin: 0, isTextBox: true, valign: "top" });
  if (src) s.addText(src, { x: x + 0.25, y: y + h - 0.42, w: w - 0.5, h: 0.3, fontFace: MONO, fontSize: 8.5, color: C.dim, margin: 0, isTextBox: true, valign: "bottom" });
}
function bullets(s, items, x, y, w, h, size = 15) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1 } })),
    { x, y, w, h, fontFace: SANS, fontSize: size, color: C.text, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 10 });
}

// 1 — cover
{
  const s = base("automated repair, judged by your tests",
    "Open with the one line. It does two things: repairs what it can prove, refuses what it cannot. Zero tokens, runs where the tests run.");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.35, w: 0.8, h: 0.8, fill: { color: C.amber }, line: { color: C.amber }, rectRadius: 0.16 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M + 0.24, y: 2.59, w: 0.32, h: 0.32, fill: { color: C.bg }, line: { color: C.bg }, rectRadius: 0.05 });
  s.addText("fluidfix", { x: M + 1.05, y: 2.1, w: 8, h: 1.3, fontFace: SANS, fontSize: 66, bold: true, color: C.ink, margin: 0, isTextBox: true, valign: "middle" });
  s.addText([{ text: "Repairs the bug. ", options: { color: C.ink } }, { text: "Refuses the guess.", options: { color: C.amber } }],
    { x: M, y: 3.55, w: 11, h: 0.9, fontFace: SANS, fontSize: 36, bold: true, margin: 0, isTextBox: true });
  body(s, "A guard for your test suite. When a regression ships, it restores the line, byte-exact, and commits — or refuses and tells you why. Zero tokens. Unattended.",
    M, 4.6, 8.4, 1.2, { fontSize: 18, color: C.muted });
  s.addText("Devieswar Kancheti  ·  devkancheti4@gmail.com", { x: M, y: 6.05, w: 8, h: 0.35, fontFace: MONO, fontSize: 11, color: C.dim, margin: 0, isTextBox: true });
}

// 2 — the problem
{
  const s = base("the problem",
    "Most fixes in real repositories are tiny and local: one file, a few lines. Measured over the full histories of three engines: raylib 85%, cglm 61%, Box2D 41% of fix commits touch exactly one file. The suite already catches these. Then a person spends the afternoon on one flipped sign.");
  title(s, "Most regressions are one file and a few lines. Each one still costs an afternoon.", 1.05, 28, 6.0);
  bullets(s, [
    "A teammate tidies a formula. One operator flips. The suite goes red.",
    "Your tests already catch it. Nothing puts it back.",
    "So a person context-switches, or an agent reads files it does not need, to restore one line.",
    "Across a year that is the maintenance budget: not the hard bugs, the many small ones."
  ], M, 2.95, 5.9, 3.3, 15);
  card(s, 7.1, 1.05, 5.55, 5.4);
  s.addText("Share of real fix commits confined to one file", { x: 7.35, y: 1.25, w: 5.1, h: 0.4, fontFace: SANS, fontSize: 14, bold: true, color: C.ink, margin: 0, isTextBox: true });
  s.addText("full git history, fix-worded commits, source files only", { x: 7.35, y: 1.62, w: 5.1, h: 0.3, fontFace: MONO, fontSize: 9, color: C.dim, margin: 0, isTextBox: true });
  [["raylib", 85.4, "1,041 fix commits"], ["cglm", 60.9, "225"], ["Box2D", 41.3, "300"]].forEach((r, i) => {
    const y = 2.35 + i * 1.1, track = 3.3, bx = 8.35;
    s.addText(r[0], { x: 7.35, y: y, w: 0.95, h: 0.4, fontFace: SANS, fontSize: 14, bold: true, color: C.text, margin: 0, isTextBox: true, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: y + 0.06, w: track, h: 0.28, fill: { color: C.raised }, line: { color: C.raised }, rectRadius: 0.06 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: y + 0.06, w: track * r[1] / 100, h: 0.28, fill: { color: C.amber }, line: { color: C.amber }, rectRadius: 0.06 });
    s.addText(Math.round(r[1]) + "%", { x: bx + track + 0.1, y: y, w: 0.8, h: 0.4, fontFace: MONO, fontSize: 14, bold: true, color: C.amber, margin: 0, isTextBox: true, valign: "middle" });
    s.addText(r[2] + " in the full history", { x: bx, y: y + 0.42, w: track + 1, h: 0.3, fontFace: MONO, fontSize: 9, color: C.dim, margin: 0, isTextBox: true });
  });
  s.addText("research/headtohead-2026-09-07/REACH.md", { x: 7.35, y: 5.75, w: 5.1, h: 0.3, fontFace: MONO, fontSize: 8.5, color: C.dim, margin: 0, isTextBox: true });
}

// 3 — what it costs today
{
  const s = base("what it costs today",
    "Two ways this gets done now. A person, at the cost of their afternoon and their focus. Or an agent: measured head to head on the same real Box2D defect, an unaided agent needed 43,006 tokens and 74 seconds to restore one flipped sign; fluidfix needed zero tokens and 6 seconds. And a plausible fix that passes the tests can still be the wrong program.");
  title(s, "Two ways it gets fixed now. Both expensive.", 1.05, 32);
  const y = 2.3, h = 3.9, w = 5.8;
  card(s, M, y, w, h); card(s, M + w + 0.35, y, w, h);
  s.addText("A person", { x: M + 0.3, y: y + 0.25, w: w - 0.6, h: 0.5, fontFace: SANS, fontSize: 20, bold: true, color: C.ink, margin: 0, isTextBox: true });
  bullets(s, ["Drops what they were doing to find one line.", "Reads the diff, reruns the suite, opens the PR, waits for review.", "Repeats it next week for the next one — the same shapes come back."],
    M + 0.3, y + 0.9, w - 0.6, 2.8, 14);
  s.addText("An agent", { x: M + w + 0.65, y: y + 0.25, w: w - 0.6, h: 0.5, fontFace: SANS, fontSize: 20, bold: true, color: C.ink, margin: 0, isTextBox: true });
  s.addText([{ text: "43,006", options: { fontFace: MONO, bold: true, color: C.amber, fontSize: 30 } }, { text: "  tokens and 73.8 s to restore one flipped sign", options: { fontSize: 13, color: C.text } }],
    { x: M + w + 0.65, y: y + 0.85, w: w - 0.6, h: 0.7, margin: 0, isTextBox: true, valign: "middle" });
  bullets(s, ["Reads files it does not need to reach the line it does.", "A plausible fix that passes the tests can still be the wrong program — and it ships.", "Same defect, fluidfix: 0 tokens, 6.3 s, byte-exact. Both arms preserved."],
    M + w + 0.65, y + 1.7, w - 0.6, 2.1, 14);
  s.addText("measured head to head on the same real Box2D defect · research/headtohead-2026-09-07", { x: M, y: 6.35, w: 12, h: 0.3, fontFace: MONO, fontSize: 8.5, color: C.dim, margin: 0, isTextBox: true });
}

// 4 — what fluidfix does
{
  const s = base("what fluidfix does",
    "It runs where your tests run: a GitHub Action, a cron job, a CI gate. When the suite goes red it finds the line, restores it, reruns your tests, and commits. When it cannot prove the fix, it refuses, leaves every byte alone, and writes down why. Seconds, not afternoons; zero tokens.");
  title(s, "It runs where your tests run. Red goes green, or it tells you why not.", 1.05, 30, 11.5);
  const steps = [["Suite goes red", "a regression is committed; nobody has to notice"], ["fluidfix finds the line", "from your failing tests, in seconds"], ["Your tests judge the fix", "every candidate runs the whole suite"], ["Restored and committed", "byte-exact, as  fluidfix: restore file:line"]];
  const sw = 2.75, gap = 0.3, y = 2.65;
  steps.forEach((st, i) => {
    const x = M + i * (sw + gap);
    card(s, x, y, sw, 1.55, i === 3);
    s.addText(st[0], { x: x + 0.22, y: y + 0.18, w: sw - 0.44, h: 0.5, fontFace: SANS, fontSize: 15, bold: true, color: C.ink, margin: 0, isTextBox: true });
    s.addText(st[1], { x: x + 0.22, y: y + 0.7, w: sw - 0.44, h: 0.75, fontFace: SANS, fontSize: 12, color: C.muted, margin: 0, isTextBox: true });
    if (i < 3) s.addText("›", { x: x + sw + 0.02, y: y + 0.45, w: gap, h: 0.6, fontFace: SANS, fontSize: 26, color: C.amber, align: "center", margin: 0, isTextBox: true });
  });
  card(s, M, 4.55, 11.9, 1.05);
  s.addText([{ text: "Or it refuses. ", options: { bold: true, color: C.amber } }, { text: "A fix it cannot prove is never written: the tree stays byte-identical, exit code 2 for CI, and a report names what was tried and which test rejected it.", options: { color: C.text } }],
    { x: M + 0.3, y: 4.7, w: 11.3, h: 0.75, fontFace: SANS, fontSize: 14, margin: 0, isTextBox: true, valign: "middle" });
  s.addText("Deploys as a GitHub Action, a cron job, or a CI gate.   ·   Python today; C/C++, Java and C# paths in alpha.   ·   No model, no tokens, nothing leaves your machine.",
    { x: M, y: 5.85, w: 12, h: 0.5, fontFace: SANS, fontSize: 12.5, color: C.muted, margin: 0, isTextBox: true });
}

// 5 — why you can trust it
{
  const s = base("why you can trust it",
    "The reason an engineering lead lets this commit to their branch: a wrong repair cannot land. Your tests are the only judge; anything they reject is rolled back byte for byte; when two fixes both pass, it refuses and writes the test that separates them; a crash mid-write is undone on the next run. Measured: zero wrong repairs in 64 runs on Python and C.");
  title(s, "A wrong repair cannot land.", 1.05, 34);
  const rows = [["Your tests are the only judge", "No model decides. Every candidate runs your whole suite before a byte is kept."],
                ["Rejected means rolled back", "A candidate that fails is restored byte for byte, line endings included."],
                ["Ambiguity is refused", "Two fixes that both pass are two programs. It refuses, and writes the test that tells them apart, for you."],
                ["Crash-safe", "Killed mid-write, the next run restores the original bytes first. Nothing to re-queue."]];
  rows.forEach((r, i) => {
    const y = 2.2 + i * 0.98;
    s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.08, w: 0.42, h: 0.42, fill: { color: C.amber }, line: { color: C.amber } });
    s.addText("✓", { x: M, y: y + 0.08, w: 0.42, h: 0.42, fontFace: SANS, fontSize: 16, bold: true, color: C.bg, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(r[0], { x: M + 0.65, y, w: 6.2, h: 0.4, fontFace: SANS, fontSize: 16, bold: true, color: C.ink, margin: 0, isTextBox: true });
    s.addText(r[1], { x: M + 0.65, y: y + 0.4, w: 6.2, h: 0.55, fontFace: SANS, fontSize: 12.5, color: C.muted, margin: 0, isTextBox: true });
  });
  stat(s, 8.3, 2.2, 4.35, 1.75, "0", "wrong repairs in 64 runs, Python and C, 2026-09-10", "research/maintenance-2026-09-10");
  stat(s, 8.3, 4.15, 4.35, 1.75, "0 tokens", "no model is invoked; nothing leaves your machine", "by construction");
}

// 6 — it learns your codebase
{
  const s = base("it learns your codebase",
    "Out of the box it repairs nine shapes of mechanical bug. The part that compounds: every incident you have had becomes a class it repairs from then on, from one example. Real history: one example from a 2016 cglm commit produced the correct repair for four fixes spanning 2016 to 2023 across four files. Your incident log is the asset.");
  title(s, "Every incident you've had becomes a repair it makes for you, forever.", 1.05, 30, 11.8);
  bullets(s, [
    "Nine shapes of mechanical bug are repaired out of the box: flipped operators, off-by-one, swapped operands, min/max, booleans, comparisons.",
    "Each incident from your own history becomes a class of its own — one worked example, written down once.",
    "From then on every member of that class is restored automatically. The same shapes come back; the fix is already there.",
    "Your incident log stops being a cost centre and becomes the thing that pays."
  ], M, 2.45, 6.6, 3.8, 15);
  stat(s, 8.0, 2.45, 4.65, 1.75, "1 → 4", "one example from 2016 produced the correct repair for four real fixes, 2016–2023, four files", "cglm history · research/laws-2026-09-07/44");
  stat(s, 8.0, 4.4, 4.65, 1.75, "9", "shapes repaired with no teaching at all", "fluidfix kinds");
}

// 7 — measured
{
  const s = base("measured, not claimed",
    "Every number here has a file behind it in the public repository; the scripts, logs and results are committed. Lead with the first row: byte-exact repairs and zero wrong.");
  title(s, "Every number has a file behind it.", 1.05, 34);
  const tiles = [["26 / 27", "byte-exact repairs, 33-bug benchmark", "docs/data/arm_a_full_results.json"],
                 ["14 / 18", "repaired across three real Python repositories (78%)", "docs/data/*-after.log"],
                 ["0", "wrong repairs in 64 runs, Python and C", "research/maintenance-2026-09-10"],
                 ["33 / 33", "defects localised to the right file", "docs/data/arm_a_full_results.json"],
                 ["46 runs", "to a byte-exact repair inside Box2D, no class written", "docs/BENCHMARK.md"],
                 ["225 / 225", "tests green on the shipping build", "full_suite_final2.log"]];
  const tw = 3.85, th = 1.85, gx = 0.28, gy = 0.28;
  tiles.forEach((t, i) => { const r = Math.floor(i / 3), c = i % 3; stat(s, M + c * (tw + gx), 2.2 + r * (th + gy), tw, th, t[0], t[1], t[2]); });
  s.addText("All measurements reproduce from the repository: github.com/devkancheti4-design/fluidfix", { x: M, y: 6.4, w: 12, h: 0.3, fontFace: MONO, fontSize: 9, color: C.dim, margin: 0, isTextBox: true });
}

// 8 — where it stops
{
  const s = base("where it stops",
    "Say the limits before they ask; engineers buy from people who state scope. It needs a test suite. It repairs one file at a time. C, C++, Java and C# are alpha. A shape it has never been shown is refused until you show it once.");
  title(s, "What it will not do, stated plainly.", 1.05, 34);
  const rows = [["It needs a test suite", "pytest today; JUnit and a C test binary in alpha. A test that cannot see the defect cannot judge the repair."],
                ["One file at a time", "Fixes that span files are out of scope today. On some engines that is most of them; on most services it is not."],
                ["Unknown shapes are refused", "Until you show it one example, it leaves the bug alone and says so. That is the feature, not a gap."],
                ["It does not reason", "It restores what it can prove and refuses the rest. Anything needing new information stays yours."]];
  rows.forEach((r, i) => {
    const c = i % 2, rr = Math.floor(i / 2), x = M + c * 6.15, y = 2.3 + rr * 2.05;
    card(s, x, y, 5.85, 1.8);
    s.addText(r[0], { x: x + 0.3, y: y + 0.25, w: 5.25, h: 0.45, fontFace: SANS, fontSize: 16, bold: true, color: C.ink, margin: 0, isTextBox: true });
    s.addText(r[1], { x: x + 0.3, y: y + 0.75, w: 5.25, h: 0.95, fontFace: SANS, fontSize: 12.5, color: C.muted, margin: 0, isTextBox: true });
  });
}

// 9 — the offer
{
  const s = base("the offer",
    "Free and open source for everything, forever — the product is public and verifiable. For a team, the pilot is the honest first step: six weeks, we run it against their history and suite, and hand back the number nobody has: how many of their regressions are this shape and what it would have saved. Credited in full against a licence. No per-seat pricing, because it costs nothing per repair.");
  title(s, "Start with the number you don't have yet.", 1.05, 34);
  const tiers = [["Open source", "Free", "AGPL-3.0", "Everything. All repair classes, every language path, unlimited repositories, no feature gate.", false],
                 ["Measurement pilot", "$5,000", "six weeks", "We run it on your history and your suite and produce the number: how many of your regressions are this shape, and what it would have saved. Credited in full against a licence.", true],
                 ["Commercial licence", "$12,000", "per year", "Closed-source use, up to 10 repositories, one language path, CI integration, the hotspots report.", false],
                 ["Studio", "$40,000", "per year", "Unlimited repositories, all paths, and we author and maintain the repair classes from your own incident history.", false]];
  const tw = 2.85, gap = 0.17, y = 2.25, th = 3.55;
  tiers.forEach((t, i) => {
    const x = M + i * (tw + gap);
    card(s, x, y, tw, th, t[4]);
    s.addText(t[0].toUpperCase(), { x: x + 0.22, y: y + 0.2, w: tw - 0.44, h: 0.3, fontFace: MONO, fontSize: 9.5, color: C.amber, charSpacing: 1.5, margin: 0, isTextBox: true });
    s.addText(t[1], { x: x + 0.22, y: y + 0.55, w: tw - 0.44, h: 0.6, fontFace: MONO, fontSize: 24, bold: true, color: C.ink, margin: 0, isTextBox: true, valign: "middle" });
    s.addText(t[2], { x: x + 0.22, y: y + 1.15, w: tw - 0.44, h: 0.3, fontFace: SANS, fontSize: 11, color: C.muted, margin: 0, isTextBox: true });
    s.addText(t[3], { x: x + 0.22, y: y + 1.55, w: tw - 0.44, h: 1.9, fontFace: SANS, fontSize: 11.5, color: C.text, margin: 0, isTextBox: true });
  });
  s.addText("No per-seat pricing: it runs on your machine and costs nothing per repair.", { x: M, y: 6.05, w: 12, h: 0.35, fontFace: SANS, fontSize: 12.5, color: C.muted, margin: 0, isTextBox: true });
}

// 10 — next step
{
  const s = base("next step", "Close on the ask: twenty minutes with one of their repositories, and they leave with a number. Leave the contact up.");
  s.addText([{ text: "Twenty minutes. ", options: { color: C.ink } }, { text: "Bring a repo.", options: { color: C.amber } }],
    { x: M, y: 1.9, w: 11, h: 1.1, fontFace: SANS, fontSize: 44, bold: true, margin: 0, isTextBox: true });
  body(s, "We point it at one repository you already have, live, and you watch it restore a real regression or refuse it and say why. Then we scope the pilot against your own history.",
    M, 3.15, 8.6, 1.3, { fontSize: 17, color: C.muted });
  card(s, M, 4.75, 7.2, 1.45);
  s.addText([{ text: "devkancheti4@gmail.com", options: { breakLine: true, color: C.ink, bold: true } }, { text: "github.com/devkancheti4-design/fluidfix   ·   pypi.org/project/fluidfix", options: { color: C.muted } }],
    { x: M + 0.3, y: 4.9, w: 6.7, h: 1.15, fontFace: MONO, fontSize: 13, margin: 0, isTextBox: true, valign: "middle", paraSpaceAfter: 6 });
  s.addText([{ text: "Repairs the bug. ", options: { color: C.ink } }, { text: "Refuses the guess.", options: { color: C.amber } }],
    { x: 8.3, y: 4.75, w: 4.4, h: 1.45, fontFace: SANS, fontSize: 20, bold: true, margin: 0, isTextBox: true, valign: "middle" });
}

const OUT = process.argv[2] || "fluidfix-deck.pptx";
pres.writeFile({ fileName: OUT }).then(f => console.log("wrote", f, "slides", n));
