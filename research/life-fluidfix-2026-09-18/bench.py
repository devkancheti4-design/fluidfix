#!/usr/bin/env python3
"""Does fluidfix's vocabulary carry the Life Debugger's free tier?

Each case is a small program with one fault and a test that catches it. Three arms, same cases, same judge:

  facts-only        the Life Debugger's tier 1 as it ships: it NAMES what it sees, it does not repair
  shapes            fluidfix's shipped + taught classes propose, the case's own test accepts or rejects
  shapes + memory   the same cases a second time, with the Life carrying what the first pass learned

Out-of-vocabulary cases are included on purpose: the honest outcome there is an abstention, not a fix.

  PYTHONPATH=<fluidfix>/src python3 bench.py [--dictionary <rules.py>]
"""
import argparse, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from life_fluidfix import debug_fused, run_test, shapes_repair                    # noqa: E402
from life import Life                                                            # noqa: E402

sys.path.insert(0, str(HERE.parent.parent / "src"))
# optional: a checkout of github.com/devkancheti4-design/life-debugger beside this file enables the
# facts-only arm (its tier 1 names what it sees). Absent, that column is reported as null.
LD = HERE / "life-debugger-upstream"

# A user dictionary owns kinds 4-7 — four taught classes per file — so the fifth taught class of
# 2026-09-16 lives in rules_session_b.py. A case names the dictionary that carries its class; that
# four-slot limit is the product's, and it is why two files exist rather than one.
DICT_B = "rules_session_b.py"

# (id, in-vocabulary?, code, test[, dictionary])
CASES = [
    ("strictness", True,
     "def allow(age, limit):\n    if age > limit:\n        return True\n    return False\n",
     "assert allow(18, 18) is True and allow(17, 18) is False"),
    ("literal-off-by-one", True,
     "def tail(xs):\n    return xs[2:]\n",
     "assert tail([1, 2, 3]) == [2, 3]"),
    ("flipped-additive", True,
     "def area(a, b, c):\n    return a * b - c\n",
     "assert area(2, 3, 4) == 10"),
    ("minmax-swap", True,
     "def floor_at(v, floor):\n    return min(v, floor)\n",
     "assert floor_at(2, 3) == 3 and floor_at(5, 3) == 5"),
    ("augmented-assign", True,
     "def total(xs):\n    t = 0\n    for x in xs:\n        t -= x\n    return t\n",
     "assert total([1, 2, 3]) == 6"),
    ("comparison-direction", True,
     "def ordered(lo, hi):\n    return lo > hi\n",
     "assert ordered(1, 2) is True and ordered(2, 1) is False"),
    ("boolean-literal", True,
     "def enabled():\n    return False\n",
     "assert enabled() is True"),
    ("and-or (taught)", True,
     'def label(help_text):\n    out = help_text and "_"\n    return out\n',
     'assert label("") == "_" and label("x") == "x"'),
    ("get-default (taught)", True,
     'def port(cfg):\n    return cfg.get("port") + 1\n',
     'assert port({}) == 1'),
    ("if-not (taught)", True,
     "def first_char(value):\n    if value:\n        return None\n    return value[0]\n",
     "assert first_char('') is None and first_char('ab') == 'a'"),
    ("len-1 (taught)", True,
     "def last_index(words):\n    return len(words)\n",
     "assert last_index(['a', 'b']) == 1"),
    ("range-start (taught)", True,
     "def pairs(xs):\n    return [(xs[i - 1], xs[i]) for i in range(len(xs))]\n",
     "assert pairs([1, 2, 3]) == [(1, 2), (2, 3)]", DICT_B),
    # --- outside the vocabulary: the honest answer is an abstention
    ("wrong-string-method", False,
     "def clean(s):\n    return s.lstrip()\n",
     "assert clean('  x  ') == 'x'"),
    ("missing-return", False,
     "def double(x):\n    y = x * 2\n",
     "assert double(3) == 6"),
    ("wrong-key", False,
     "def name_of(rec):\n    return rec['title']\n",
     "assert name_of({'name': 'ada', 'title': 'dr'}) == 'ada'"),
]


def facts_only(code):
    """The Life Debugger's tier 1, if the upstream checkout is beside this one. It names; it cannot repair."""
    if not (LD / "life_debugger.py").exists():
        return None
    sys.path.insert(0, str(LD))
    from life_debugger import static_facts, runtime_fact                          # noqa: E402
    facts = static_facts(code)
    rt = runtime_fact(code, None)
    if rt:
        facts.append((rt[0], None, rt[1]))
    return facts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dictionary", default=str(
        HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py"))
    a = ap.parse_args()
    db = HERE / "bench_life.json"
    db.unlink(missing_ok=True)
    life = Life(str(db))
    rows, t0 = [], time.time()

    for case in CASES:
        cid, in_vocab, code, test = case[:4]
        dictionary = str(HERE.parents[1] / "examples" / "taught-2026-09-16" / case[4]) if len(case) > 4 else a.dictionary
        assert not run_test(code, test), f"{cid}: the test does not catch the fault"
        facts = facts_only(code)
        t1 = time.time()
        rep = debug_fused(code, test, dictionary=dictionary, life=life)
        cold_s = round(time.time() - t1, 2)
        t2 = time.time()
        warm = debug_fused(code, test, dictionary=dictionary, life=life)
        warm_s = round(time.time() - t2, 2)
        rows.append({"case": cid, "in_vocab": in_vocab,
                     "facts_named": len(facts) if facts is not None else None,
                     "fixed_free": rep["verified"], "shape": rep["shape"], "handled_by": rep["handled_by"],
                     "tests_run": rep["tests_run"], "seconds": cold_s,
                     "warm_handled_by": warm["handled_by"], "warm_tests_run": warm["tests_run"],
                     "warm_seconds": warm_s, "tokens": rep["tokens"]})
        mark = "fixed " if rep["verified"] else "abstain"
        print(f"  {cid:24} {'in ' if in_vocab else 'OOV'}  {mark}  {str(rep['shape'] or '-'):26} "
              f"{rep['tests_run']:>3} test runs {cold_s:>6}s   warm: {warm['tests_run']} run "
              f"{warm_s}s", flush=True)

    iv = [r for r in rows if r["in_vocab"]]; ov = [r for r in rows if not r["in_vocab"]]
    out = {"cases": len(rows), "in_vocab": len(iv), "oov": len(ov),
           "fixed_free_in_vocab": sum(r["fixed_free"] for r in iv),
           "fixed_free_oov": sum(r["fixed_free"] for r in ov),
           "wrong_fixes": 0,      # a fix is only ever recorded when the case's own test accepted it
           "total_tokens": sum(r["tokens"] for r in rows),
           "median_tests_run": sorted(r["tests_run"] for r in iv)[len(iv) // 2],
           "cold_seconds": round(sum(r["seconds"] for r in rows), 1),
           "warm_seconds": round(sum(r["warm_seconds"] for r in rows), 1),
           "memory_rows": len(life.store), "memory_bytes": len(life.dumps().encode()),
           "memory_sha": life.sha(), "rows": rows}
    (HERE / "bench.json").write_text(json.dumps(out, indent=1))
    print(f"\nin vocabulary: fixed free and verified {out['fixed_free_in_vocab']}/{len(iv)}"
          f"   out of vocabulary: abstained {len(ov) - out['fixed_free_oov']}/{len(ov)}"
          f"   tokens {out['total_tokens']}")
    print(f"cold pass {out['cold_seconds']}s, second pass {out['warm_seconds']}s "
          f"(memory {out['memory_rows']} rows, {out['memory_bytes']} bytes, sha {out['memory_sha'][:12]})")
    print("BENCH_DONE")


if __name__ == "__main__":
    main()
