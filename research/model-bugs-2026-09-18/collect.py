#!/usr/bin/env python3
"""Ask a model to write sixteen small functions from prose alone, then keep the ones its own tests reject.

The bugs measured here are not seeded by me. A model is given a signature and a docstring, never the tests,
and writes whatever it writes. Every implementation is then run against the hidden tests; the failures are
this file's output, and `repair.py` hands them to fluidfix with those same tests as the judge.

  python3 collect.py --model qwen3.5:4b            # a local model through Ollama
  python3 collect.py --from-file answers.json      # implementations written elsewhere (e.g. by a subagent)
"""
import argparse, json, re, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import importlib                                                          # noqa: E402

PROMPT = """Write the body of this Python function. Return ONLY the complete function, no commentary, no
tests, no examples, no markdown fence.

{spec}
"""


def ask_ollama(model, spec, host="http://localhost:11434"):
    body = json.dumps({"model": model, "stream": False, "think": False,
                       "options": {"temperature": 0, "num_predict": 400},
                       "messages": [{"role": "user", "content": PROMPT.format(spec=spec)}]}).encode()
    req = urllib.request.Request(host + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["message"]["content"]


def clean(code: str) -> str:
    """Take the function out of whatever wrapping came back."""
    m = re.search(r"```(?:python)?\s*(.*?)```", code, re.S)
    if m:
        code = m.group(1)
    lines = code.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("def ") or l.startswith("import ")
                  or l.startswith("from ")), 0)
    return "\n".join(lines[start:]).strip() + "\n"


def run_tests(code: str, tests: list[str]) -> tuple[bool, str]:
    script = code + "\n" + "\n".join(tests) + "\n"
    try:
        p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if p.returncode == 0:
        return True, ""
    tail = [l for l in p.stderr.strip().split("\n") if l.strip()]
    return False, (tail[-1] if tail else "failed")[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--from-file"); ap.add_argument("--label")
    ap.add_argument("--specs", default="specs", help="the spec module: specs or specs_hard")
    a = ap.parse_args()
    SPECS = importlib.import_module(a.specs).SPECS
    label = (a.label or a.model or "file") + ("" if a.specs == "specs" else "-hard")
    written = json.load(open(a.from_file)) if a.from_file else {}

    rows = []
    for name, spec, tests in SPECS:
        code = clean(written[name]) if a.from_file else clean(ask_ollama(a.model, spec))
        ok, why = run_tests(code, tests)
        rows.append({"name": name, "code": code, "tests": tests, "passed": ok, "why": why})
        print(f"  {name:18} {'passes' if ok else 'FAILS   ' + why[:70]}", flush=True)
    out = {"author": label, "written": len(rows), "failed": sum(not r['passed'] for r in rows), "rows": rows}
    (HERE / f"written_{re.sub(r'[^A-Za-z0-9.]+', '-', label)}.json").write_text(json.dumps(out, indent=1))
    print(f"\n{label}: {out['failed']} of {out['written']} implementations fail their own hidden tests")


if __name__ == "__main__":
    main()
