#!/usr/bin/env python3
"""LLM fusion prototype: the escalation ladder, with the model as AUTHOR, never judge.

  tier 0  fluidfix guard with the shipped + taught rules          0 tokens
  tier 1  the model authors a RULE from the refusal packet        small model
  tier 2  the model authors a ONE-SHOT FIX (as a one-line rule)   stronger model
  tier 3  human (this script stops and reports)

Every model output becomes a candidate that goes through the same suite, byte-exact
rollback, ambiguity probe and law ruling as a hand-written rule. Nothing is written
by the model. Tokens are counted from the API's own usage fields.

  python3 fuse.py <repo> [--dictionary rules.py] [--backend anthropic|mock]
                  [--tier1-model ID] [--tier2-model ID] [--max-tier 2] [--report out.json]
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

PY = sys.executable
GUARD = [PY, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit"]
BUDGET: list = []   # ["--budget", "300"] when the caller bounds each guard run

CONTRACT = """You write ONE fault-class rule for fluidfix, a tool that repairs a regression when a
test suite goes red. A rule has four parts and is judged only by the suite, so be precise, not clever.

Return ONLY a JSON object with these keys:
  "example_before": the defective line exactly as it appears (no indentation),
  "example_after":  the same line fixed,
  "name":           a short hyphenated slug,
  "description":    one sentence stating what an observer SEES on such a line (a fact, never an instruction),
  "signal":         a Python regex that matches lines that CAN exhibit this fault; anchor it on the class's own tokens,
  "applier":        Python source of a function  def fix(line, o): ...  returning the corrected line (a str),
                    a list of candidate strs, or [SpanEdit(start, end, text)] for several lines that must change together.
                    `re` and `SpanEdit` are available. If the line is not this class, return line unchanged. Never raise.

Rules: the fix must be derivable from the line plus what the repository already contains. Do not widen the
signal beyond the class. Do not invent facts that are not in the packet. Preserve indentation: the applier
receives the full line including leading spaces and must return lines with the same leading spaces."""

CONTRACT2 = """You propose a direct fix for ONE defective region. The test suite will judge every proposal; a wrong
proposal costs nothing, a missing correct one costs the repair, so give up to three DIFFERENT complete
replacements, best first. Return ONLY a JSON object:
  {"line": <the defective line exactly, including leading spaces>,
   "replacements": [<full replacement line 1 with the same leading spaces>, ...]}
If the fix needs several consecutive lines, give the whole block as one string with newlines in each replacement.
Never touch tests. Never invent identifiers that do not appear in the packet. The packet shows source lines with a
"NNNN| " line-number gutter; the gutter is not part of the line."""


def sh(cmd, cwd, env=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def packet(repo: Path, refusal: dict, max_lines=400) -> dict:
    """The compact context, built by the product's own observation packet (fluidfix.localize.build_packet):
    the compressed failing output and the lines of the suspect file that the failing test executed, numbered.
    The first design (regions +-3 around rejected candidates, executed_lines capped at 80) never contained the
    defect line in any out-of-vocabulary case (measured on click, 2026-09-16); this one shows the executed
    lines uncapped up to `max_lines`, spread-sampled beyond that with `truncated` set, exactly as the guard's
    escalation sees them. The last commit's diff is deliberately NOT included: in the bench it is the answer."""
    from fluidfix import Oracle
    from fluidfix.localize import build_packet
    files = refusal.get("candidates") or []
    top = files[0] if files else None
    sight, shown, truncated = "", 0, False
    if top and (repo / top).exists():
        # FULL sight, as the guard's escalation sees it (max_lines=10**9: no signal-token filter, no sampling).
        # Measured 2026-09-16 on click notdrop-1: with max_lines=240 the product's filter kept only lines carrying a
        # signal token, so `if value:` (the defect) was dropped and the sampler repeated the 48 survivors five times.
        pk = build_packet(Oracle(str(repo), python=PY), top, max_lines=10**9)
        if pk is not None:
            lines = sorted(set(pk.lines))
            if len(lines) > max_lines:           # our own cap: a unique spread sample, flagged
                stride = len(lines) / max_lines; lines = sorted({lines[int(i * stride)] for i in range(max_lines)}); truncated = True
            pk.lines = lines
            sight, shown = pk.render("REFUSED"), len(lines)
    if not sight:
        red = sh([PY, "-m", "pytest", "-q", "-x", "--tb=short", "-p", "no:cacheprovider"], repo)
        sight = "\n".join(l for l in (red.stdout or "").splitlines() if l.strip())[-3000:]
    rejected = [{"at": c["at"], "tried": c["tried"].strip(), "why": c["why"][:80]} for c in refusal.get("rejected_candidates", [])[:20]]
    return {"file": top, "other_suspects": files[1:5], "sight": sight, "lines_shown": shown, "truncated": truncated,
            "rejected_by_the_suite": rejected, "hint": refusal.get("hint", "")[:300]}


class Anthropic:
    def __init__(self, tier1, tier2):
        import anthropic
        self.c = anthropic.Anthropic(); self.m = {1: tier1, 2: tier2}
    def ask(self, tier, system, user, max_tokens=900):
        r = self.c.messages.create(model=self.m[tier], max_tokens=max_tokens,
                                   system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                                   messages=[{"role": "user", "content": user}])
        u = r.usage
        usage = {"input": u.input_tokens, "output": u.output_tokens,
                 "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0, "model": self.m[tier]}
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text"), usage


class Ollama:
    """Local models through Ollama's chat API; token counts from the runtime itself."""
    def __init__(self, tier1, tier2, host="http://localhost:11434"):
        self.m = {1: tier1, 2: tier2}; self.host = host
    def ask(self, tier, system, user, max_tokens=900):
        import urllib.request
        body = json.dumps({"model": self.m[tier], "stream": False, "format": "json", "think": False,
                           "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": 8192},
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.host + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r: d = json.load(r)
        usage = {"input": d.get("prompt_eval_count", 0), "output": d.get("eval_count", 0), "cache_read": 0, "cache_write": 0,
                 "model": self.m[tier], "seconds": round(d.get("total_duration", 0) / 1e9, 1)}
        return d["message"]["content"], usage


class FileAuthor:
    """A human or an in-session assistant authors the answer: the packet is written to
    <dir>/packet_tierN.json; if <dir>/answer_tierN.json exists it is used, else exit 3."""
    def __init__(self, d, label="file"):
        self.d = Path(d); self.d.mkdir(parents=True, exist_ok=True); self.label = label
    def ask(self, tier, system, user, max_tokens=900):
        (self.d / f"packet_tier{tier}.json").write_text(json.dumps({"system": system, "user": json.loads(user)}, indent=1))
        ans = self.d / f"answer_tier{tier}.json"
        if not ans.exists():
            print(json.dumps({"outcome": "awaiting-author", "tier": tier, "packet": str(self.d / f"packet_tier{tier}.json")})); sys.exit(3)
        a = ans.read_text()
        return a, {"input": (len(system) + len(user)) // 4, "output": len(a) // 4, "cache_read": 0, "cache_write": 0, "model": self.label, "approx": True}


class Mock:
    """Plumbing test: returns canned answers, counts 'tokens' as characters/4."""
    def __init__(self, answers): self.answers = answers
    def ask(self, tier, system, user, max_tokens=900):
        a = json.dumps(self.answers[str(tier)])
        return a, {"input": (len(system) + len(user)) // 4, "output": len(a) // 4, "cache_read": 0, "cache_write": 0, "model": "mock"}


def parse_json(text):
    """The author's reply as JSON, or None. A malformed reply (measured: gemma3:4b and qwen3.5:4b hit the
    output cap inside a string) is a failed tier, not a crash."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except json.JSONDecodeError: return None


def validate_rule(repo: Path, top: str, rule: dict) -> tuple[bool, str]:
    try: sig = re.compile(rule["signal"])
    except Exception as e: return False, f"bad signal: {e}"
    src = (repo / top).read_text().split("\n") if top else []
    hits = [(i + 1, l) for i, l in enumerate(src) if sig.search(l)]
    if not hits: return False, "signal matches no line in the suspect file"
    if len(hits) > 12: return False, f"signal too broad: {len(hits)} lines in one file"
    ns = {"re": re}
    try:
        from fluidfix.acts import SpanEdit; ns["SpanEdit"] = SpanEdit
        exec(rule["applier"], ns)
        fix = ns["fix"]
        # every matching line, with its real line number: a context-aware applier may rightly decline some hits
        # (measured 2026-09-16: a correct guard rule was rejected as a no-op when tested on the first hit at lineno=1)
        changed = 0
        for ln, line in hits:
            out = fix(line, type("O", (), {"lineno": ln, "all_lines": src, "root": str(repo), "kinds": [], "note": ""})())
            cands = out if isinstance(out, list) else [out]
            if not all(isinstance(c, str) and c == line for c in cands): changed += 1
    except Exception as e: return False, f"applier failed: {e}"
    if not changed: return False, "applier is a no-op on every matched line"
    return True, f"ok: {len(hits)} matching line(s), applier changes {changed}"


def write_dictionary(repo: Path, base: str | None, rules: list[dict]) -> str:
    """One combined dictionary: the user's rules plus the model-authored ones, with provenance."""
    body = (repo / base).read_text() + "\n\n" if base and (repo / base).exists() else ""
    used = set(int(k) for k in re.findall(r"register\(\s*(\d+)", body))
    free = [k for k in (4, 5, 6, 7) if k not in used]
    for r in rules:
        k = free.pop(0) if free else 7
        body += (f"# --- authored by {r['_model']} from refusal {r['_incident']} ({r['_tier']}) ---\n"
                 f"#   {r.get('example_before','')}\n#   {r.get('example_after','')}\n"
                 f"{r['applier']}\n"
                 f"register({k}, {r['name']!r}, {r['description']!r}, re.compile({r['signal']!r}), fix)\n"
                 f"del fix\n\n")
    (repo / "rules_fused.py").write_text(body)
    return "rules_fused.py"


def run_guard(repo: Path, env, dictionary: str | None):
    cmd = GUARD + BUDGET + (["--dictionary", dictionary] if dictionary else [])
    t0 = time.time(); g = sh(cmd, repo, env=env); wall = time.time() - t0
    ref = repo / ".fluidfix" / "last_refusal.json"
    refusal = json.load(open(ref)) if (g.returncode == 2 and ref.exists()) else None
    m = re.search(r"repaired line (\d+) in (\d+) suite runs \(([\d.]+)s\)", g.stdout)
    return {"exit": g.returncode, "wall": round(wall, 1), "suite_runs": int(m.group(2)) if m else None,
            "stdout": g.stdout[-600:], "refusal": refusal}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo"); ap.add_argument("--dictionary"); ap.add_argument("--backend", default="anthropic")
    ap.add_argument("--tier1-model", default="claude-haiku-4-5-20251001"); ap.add_argument("--tier2-model", default="claude-sonnet-5")
    ap.add_argument("--max-tier", type=int, default=2); ap.add_argument("--report"); ap.add_argument("--mock-answers")
    ap.add_argument("--incident", default="incident"); ap.add_argument("--author-dir"); ap.add_argument("--author-label", default="file")
    ap.add_argument("--refusal", help="a recorded tier-0 refusal report: start the ladder from it instead of re-running tier 0")
    ap.add_argument("--budget", type=int, help="wall-clock budget (s) for each guard run the ladder makes")
    a = ap.parse_args()
    if a.budget: BUDGET[:] = ["--budget", str(a.budget)]
    repo = Path(a.repo).resolve(); env = dict(os.environ)
    if a.backend == "mock": llm = Mock(json.load(open(a.mock_answers)))
    elif a.backend == "ollama": llm = Ollama(a.tier1_model, a.tier2_model)
    elif a.backend.startswith("file"): llm = FileAuthor(a.author_dir or (repo / ".fluidfix" / "author"), a.author_label)
    else: llm = Anthropic(a.tier1_model, a.tier2_model)
    report = {"repo": str(repo), "tiers": [], "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}}
    def spend(u):
        for k in ("input", "output", "cache_read", "cache_write"): report["tokens"][k] += u[k]

    if a.refusal:   # tier 0 already measured (bench_real.py): replay from its report
        ref = json.load(open(a.refusal))
        r0 = {"exit": 2, "wall": round(ref.get("seconds", 0), 1), "suite_runs": None, "stdout": "", "refusal": ref, "recorded": a.refusal}
    else:
        r0 = run_guard(repo, env, a.dictionary)
    report["tiers"].append({"tier": 0, **{k: v for k, v in r0.items() if k != "refusal"}})
    if r0["exit"] != 2 or not r0["refusal"] or a.max_tier < 1:
        report["outcome"] = "tier0"; return finish(report, a)

    # ---- tier 1: author a rule
    pk = packet(repo, r0["refusal"])
    text, u = llm.ask(1, CONTRACT, json.dumps(pk, indent=1)); spend(u)
    rule = parse_json(text) or {}
    ok, why = validate_rule(repo, pk["file"], rule) if rule else (False, "no JSON")
    t1 = {"tier": 1, "model": u["model"], "tokens": u, "valid": ok, "why": why, "rule": {k: rule.get(k) for k in ("name", "signal", "example_before", "example_after")}}
    if ok:
        rule.update(_model=u["model"], _incident=a.incident, _tier="tier1")
        d = write_dictionary(repo, a.dictionary, [rule])
        r1 = run_guard(repo, env, d); t1.update({k: v for k, v in r1.items() if k != "refusal"})
        report["tiers"].append(t1)
        if r1["exit"] == 0: report["outcome"] = "tier1"; return finish(report, a)
        refusal = r1["refusal"] or r0["refusal"]
    else:
        report["tiers"].append(t1); refusal = r0["refusal"]
    if a.max_tier < 2: report["outcome"] = "refused-after-tier1"; return finish(report, a)

    # ---- tier 2: author a one-shot fix, still judged by the suite
    pk2 = packet(repo, refusal)
    text, u = llm.ask(2, CONTRACT2, json.dumps(pk2, indent=1), max_tokens=1200); spend(u)
    fix = parse_json(text) or {}
    _gut = lambda t: "\n".join(re.sub(r"^\s*\d{1,5}\| ?", "", l) for l in t.split("\n"))   # the packet shows "NNNN| " gutters; an author that copies one is not wrong about the code
    line = _gut(fix.get("line", "")); reps = [r for r in (_gut(x) for x in fix.get("replacements", []) if isinstance(x, str)) if r != line]
    t2 = {"tier": 2, "model": u["model"], "tokens": u, "proposals": len(reps), "line": line[:160], "replacements": [r[:160] for r in reps[:3]]}
    if line and reps:
        from fluidfix.acts import SpanEdit  # noqa: F401  (import check)
        n = line.count("\n") + 1
        applier = ("def fix(line, o):\n    L = " + repr(line.split("\n")[0]) + "\n    if line != L: return [line]\n"
                   + ("    return " + repr(reps) + "\n" if n == 1 else
                      "    return [SpanEdit(o.lineno, o.lineno + " + str(n - 1) + ", r) for r in " + repr(reps) + "]\n"))
        rule2 = {"name": "one-shot-fix", "description": "a line the model proposed a direct replacement for",
                 "signal": "^" + re.escape(line.split("\n")[0]) + "$", "applier": applier,
                 "example_before": line.split("\n")[0].strip(), "example_after": reps[0].split("\n")[0].strip(),
                 "_model": u["model"], "_incident": a.incident, "_tier": "tier2"}
        d = write_dictionary(repo, a.dictionary, [rule2])
        r2 = run_guard(repo, env, d); t2.update({k: v for k, v in r2.items() if k != "refusal"})
        report["tiers"].append(t2)
        report["outcome"] = "tier2" if r2["exit"] == 0 else "refused-after-tier2"
    else:
        report["tiers"].append(t2); report["outcome"] = "refused-after-tier2"
    return finish(report, a)


def finish(report, a):
    t = report["tokens"]; report["tokens"]["total"] = t["input"] + t["output"] + t["cache_read"] + t["cache_write"]
    if a.report: Path(a.report).write_text(json.dumps(report, indent=1))
    print(json.dumps({"outcome": report["outcome"], "tokens": report["tokens"], "tiers": [(x["tier"], x.get("exit")) for x in report["tiers"]]}))
    return 0 if report["outcome"] in ("tier0", "tier1", "tier2") else 2


if __name__ == "__main__":
    sys.exit(main())
