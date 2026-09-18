#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One specification, one model, many samples: the distribution a single generation collapses.

A program is a TOTAL FUNCTION. One generation therefore encodes the model's answer to unboundedly many
inputs it was never shown, and running it recovers them for free. Sample the same model on the same prompt
many times and you no longer have one answer — you have the distribution the model was drawing from, read
out behaviourally, with no logprobs and no access to anything inside.

That separates two things a single sample cannot tell apart:

  SURFACE variation    different source text, identical behaviour everywhere the pool can see —
                       many ways of writing the same function
  BEHAVIOURAL variation different answers on some input — the prompt genuinely did not determine it

The second is the only one that can ever hurt you, and it is invisible to a test suite that passes.

  PYTHONPATH=<fluidfix>/src python3 sampling.py [--model qwen3.5:4b] [--n 20] [--temp 0.8]
"""
from __future__ import annotations

import argparse, ast, hashlib, json, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "certify-2026-09-18"))
sys.path.insert(0, str(HERE.parent / "model-bugs-2026-09-18"))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import certify as C                                                    # noqa: E402
from fluidfix import differ                                            # noqa: E402
import collect                                                         # noqa: E402
import specs as S_ORD, specs_hard as S_HARD                            # noqa: E402

WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "79a458ef-6d23-4133-bc16-eb60d3ddd08d/scratchpad/sampling")

# specs already shown to be under-determined, plus one that was not
PICK = ["page_count", "clip_exclusive", "progress", "windows", "between"]


def ask(model, spec, temp):
    import urllib.request
    body = json.dumps({"model": model, "stream": False, "think": False,
                       "options": {"temperature": temp, "num_predict": 400},
                       "messages": [{"role": "user",
                                     "content": collect.PROMPT.format(spec=spec)}]}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:4b"); ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--temp", type=float, default=0.8)
    a = ap.parse_args()
    allspecs = {n: (s, t) for n, s, t in list(S_ORD.SPECS) + list(S_HARD.SPECS)}
    WORK.mkdir(parents=True, exist_ok=True)
    report, t0 = [], time.time()

    for spec_name in PICK:
        spec, tests = allspecs[spec_name]
        root = WORK / spec_name
        arity = len(ast.parse(spec + "\n    pass\n").body[0].args.args)
        C.build_repo(root, spec + "\n    pass\n", tests)
        pool = differ.build_pool(differ.harvest_seeds(str(root), spec_name, arity), arity)

        texts, behaviours, passed, rows = Counter(), Counter(), 0, []
        for i in range(a.n):
            code = collect.clean(ask(a.model, spec, a.temp))
            ok, _why = collect.run_tests(code, tests)
            passed += ok
            texts[hashlib.md5(code.encode()).hexdigest()[:8]] += 1
            res = differ.evaluate(str(root), C.MODULE, code, "pkg", spec_name, pool)
            vals = res.get("values")
            key = hashlib.md5(json.dumps(vals, default=str).encode()).hexdigest()[:8] if vals else "ERR"
            behaviours[key] += 1
            rows.append({"passed": ok, "text": hashlib.md5(code.encode()).hexdigest()[:8],
                         "behaviour": key, "values": vals, "code": code})
        # per-input spread among the samples that PASS
        good = [r for r in rows if r["passed"] and r["values"]]
        spread = []
        for i in range(len(pool)):
            answers = Counter(str(r["values"][i]) for r in good if i < len(r["values"]))
            if len(answers) > 1:
                spread.append({"input": pool[i], "answers": dict(answers)})
        rec = {"spec": spec_name, "n": a.n, "temp": a.temp, "passed": passed, "pool": len(pool),
               "distinct_texts": len(texts), "distinct_behaviours": len(behaviours),
               "undetermined_inputs": spread}
        report.append(rec)
        print(f"{spec_name:16} {passed}/{a.n} pass | {len(texts):>2} distinct programs -> "
              f"{len(behaviours):>2} distinct behaviours | "
              f"{len(spread)} of {len(pool)} inputs the samples disagree on", flush=True)
        for s in spread[:3]:
            print(f"      {str(s['input']):26} " +
                  ", ".join(f"{k}x{v}" for k, v in sorted(s['answers'].items(), key=lambda kv: -kv[1])),
                  flush=True)

    (HERE / f"sampling_{a.model.replace(':', '-')}.json").write_text(json.dumps(
        {"model": a.model, "n": a.n, "temp": a.temp, "specs": report}, indent=1, default=str))
    print(f"\n{round(time.time() - t0, 1)}s  SAMPLING_DONE")


if __name__ == "__main__":
    main()
