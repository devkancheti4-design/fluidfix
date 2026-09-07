#!/usr/bin/env python
"""Pool both victims' runs and print the rate table with its denominators."""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Ships that are byte-different from the original but are the SAME PROGRAM
# (multiplication commutes). Judged by hand, listed explicitly so the rate is
# auditable rather than asserted.
EQUIVALENT = {("runs2", 26)}


def load():
    rows = []
    for runs in ("runs", "runs2"):
        for p in sorted(glob.glob(os.path.join(HERE, runs, "*", "result.json"))):
            r = json.load(open(p))
            r["_runs"] = runs
            r["_dir"] = os.path.dirname(p)
            rows.append(r)
    return rows


def main():
    rows = [r for r in load()
            if not r["orig"].lstrip().startswith("Same rule as victim")]
    injected = len(rows)
    detected = [r for r in rows if r["suite_red"]]
    shipped = [r for r in detected if (r.get("report") or {}).get("repaired")]
    refused = [r for r in detected if not (r.get("report") or {}).get("repaired")]

    not_exact = [r for r in shipped if not r["final_equals_pristine"]]
    equiv = [r for r in not_exact if (r["_runs"], r["id"]) in EQUIVALENT]
    wrong = [r for r in not_exact if (r["_runs"], r["id"]) not in EQUIVALENT]
    multigreen = [r for r in shipped if len(r.get("greens") or []) > 1]
    dirty = [r for r in detected
             if not (r.get("report") or {}).get("repaired")
             and not r["final_equals_pristine"] and not r["final_equals_mutant"]]

    print(f"injected in-vocabulary defects            : {injected}")
    print(f"  undetected by the weak suite (green)    : {injected - len(detected)}")
    print(f"  DETECTED -> fluidfix asked to repair    : {len(detected)}   <-- denominator")
    print(f"    accepted repair shipped to disk       : {len(shipped)}")
    print(f"    refused                               : {len(refused)}")
    print()
    print(f"WRONG PROGRAM SHIPPED  {len(wrong)}/{len(detected)} detected defects "
          f"= {100*len(wrong)/len(detected):.1f}%")
    print(f"                       {len(wrong)}/{len(shipped)} accepted repairs "
          f"= {100*len(wrong)/len(shipped):.1f}%")
    print(f"NOT BYTE-EXACT         {len(not_exact)}/{len(shipped)} accepted repairs "
          f"= {100*len(not_exact)/len(shipped):.1f}%  "
          f"({len(wrong)} wrong program + {len(equiv)} equivalent respelling)")
    print(f"SHIPPED WITH >1 GREEN  {len(multigreen)}/{len(shipped)} accepted repairs "
          f"= {100*len(multigreen)/len(shipped):.1f}%  "
          f"(a second, different passing program was in hand and unreported)")
    print(f"tree left dirty after a refusal           : {len(dirty)}")
    print()
    print("--- every wrong program shipped ---")
    for r in wrong:
        print(f"  {r['_runs']}/{r['id']:02d}  {r['_dir'].split('03-weak-assert/')[-1]}")
        print(f"     original : {r['orig'].strip()}")
        print(f"     defect   : {r['mutant'].strip()}")
        print(f"     SHIPPED  : {r['final_line'].strip()}")
        print(f"     greens   : {[g.strip() for g in (r['greens'] or [])]}")
        print(f"     reason   : {r['reason']}")
    print()
    print("--- byte-different but same program ---")
    for r in equiv:
        print(f"  {r['_runs']}/{r['id']:02d}  {r['orig'].strip()}  ->  "
              f"{r['final_line'].strip()}")
    print()
    print("--- shipped while holding a second, different green ---")
    for r in multigreen:
        mark = "WRONG" if r in wrong else ("equiv" if r in equiv else "ok")
        print(f"  {r['_runs']}/{r['id']:02d} [{mark}] greens="
              f"{[g.strip() for g in r['greens']]}")


if __name__ == "__main__":
    main()
