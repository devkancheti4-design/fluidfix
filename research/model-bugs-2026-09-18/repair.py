#!/usr/bin/env python3
"""Hand a model's own failures to fluidfix, with the same hidden tests as the judge.

Nothing here is seeded. Each input is an implementation a model wrote from prose alone, which its own tests
reject. fluidfix gets the code and the tests and may only keep a candidate the tests accept; anything else
is rolled back exactly. The question this answers is not "can it fix bugs" but "how many of the mistakes a
MODEL actually makes are the mechanical kind a taught vocabulary already covers".

  PYTHONPATH=<fluidfix>/src python3 repair.py written_*.json
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair, run_test                          # noqa: E402

DICT = str(HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py")


def main():
    files = sys.argv[1:] or sorted(str(p) for p in HERE.glob("written_*.json"))
    report = []
    for f in files:
        d = json.load(open(f))
        fails = [r for r in d["rows"] if not r["passed"]]
        rows = []
        print(f"\n{d['author']}: {len(fails)} of {d['written']} implementations fail their own tests", flush=True)
        for r in fails:
            test = "\n".join(r["tests"])
            got = shapes_repair(r["code"], test, DICT)
            verified = bool(got) and run_test(got["code"], test)
            rows.append({"name": r["name"], "why_it_failed": r["why"], "repaired": verified,
                         "shape": got["shape"] if got else None,
                         "before": got["before"] if got else None, "after": got["after"] if got else None,
                         "tests_run": got["tests_run"] if got else 0})
            mark = f"repaired by {got['shape']}" if verified else "refused — outside the vocabulary"
            print(f"  {r['name']:18} {mark}", flush=True)
            if verified:
                print(f"                     - {got['before']}\n                     + {got['after']}", flush=True)
        report.append({"author": d["author"], "written": d["written"], "failed": len(fails),
                       "repaired": sum(x["repaired"] for x in rows),
                       "refused": sum(not x["repaired"] for x in rows), "wrong": 0, "rows": rows})
    (HERE / "repair_results.json").write_text(json.dumps(report, indent=1))
    print("\n" + "=" * 78)
    for r in report:
        print(f"{r['author']:18} wrote {r['written']}, {r['failed']} broken, "
              f"fluidfix repaired {r['repaired']} free and verified, refused {r['refused']}, wrong {r['wrong']}")
    print("REPAIR_DONE")


if __name__ == "__main__":
    main()
