"""Byte-exact audit: diff every repaired file against the pristine original.

For each fixture: write the PRISTINE (correct) file, write the suite, then
overwrite with the DEFECT bytes and run the guard exactly as a user would.
Afterwards compare the file on disk to the pristine bytes, byte for byte,
plus st_mode. Nothing here weakens fluidfix: the stock API, stock env.

    ./rt 1800 .venv/bin/python audit.py            # all fixtures
    ./rt 300  .venv/bin/python audit.py 03 11      # named fixtures only
"""
import json
import os
import shutil
import stat
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from fluidfix import MechanicalObserver, Oracle, guard_once   # noqa: E402
from fixtures2 import F                                       # noqa: E402

PY = os.path.join(ROOT, ".venv", "bin", "python")
# == the documented --suite-timeout flag. 300s (the default) only
# buys clock for non-terminating candidates, which is not this
# target; no defence is disabled by lowering it.
SUITE_TIMEOUT = 45
WORK = os.path.join(HERE, "work")


def eol_profile(b: bytes) -> dict:
    crlf = b.count(b"\r\n")
    return {"crlf": crlf, "lone_lf": b.count(b"\n") - crlf,
            "lone_cr": b.count(b"\r") - crlf,
            "final_newline": b.endswith(b"\n") or b.endswith(b"\r"),
            "bom": b.startswith(b"\xef\xbb\xbf"), "len": len(b)}


def first_diff(a: bytes, b: bytes):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return None if len(a) == len(b) else n


def line_diff(pristine: bytes, got: bytes):
    """Per-line byte diff, endings included. Lines split on \\n, keepends."""
    pa = pristine.split(b"\n")
    pb = got.split(b"\n")
    out = []
    for i in range(max(len(pa), len(pb))):
        x = pa[i] if i < len(pa) else None
        y = pb[i] if i < len(pb) else None
        if x != y:
            out.append({"line": i + 1, "pristine": None if x is None else repr(x),
                        "on_disk": None if y is None else repr(y)})
    return out


def run_one(fixture) -> dict:
    name = fixture["name"]
    d = os.path.join(WORK, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    mod = os.path.join(d, "mod.py")
    with open(mod, "wb") as fh:
        fh.write(fixture["pristine"])
    os.chmod(mod, fixture["mode"])
    with open(os.path.join(d, "test_mod.py"), "wb") as fh:
        fh.write(fixture["test"])
    pristine = open(mod, "rb").read()
    pmode = stat.S_IMODE(os.stat(mod).st_mode)

    # sanity: the pristine program must be GREEN before we inject anything.
    oracle = Oracle(d, python=PY, timeout=SUITE_TIMEOUT)
    try:
        pre_green = oracle.green()
    except Exception as e:                        # noqa: BLE001
        return {"name": name, "note": fixture["note"], "error": f"pre-green: {e!r}"}

    with open(mod, "wb") as fh:
        fh.write(fixture["defect"])
    os.chmod(mod, fixture["mode"])
    defect = open(mod, "rb").read()

    t0 = time.time()
    err = None
    try:
        report = guard_once(Oracle(d, python=PY, timeout=SUITE_TIMEOUT), MechanicalObserver())
        status, rfile = report.status, report.file
        reason = (report.hint or "") or (report.result.reason
                                         if report.result else "")
        summary = report.summary()
        res = report.result
        restored_original = getattr(res, "restored_original", None) if res else None
        greens = list(getattr(res, "greens", []) or []) if res else []
        new_line = getattr(res, "new_line", None) if res else None
        old_line = getattr(res, "old_line", None) if res else None
        lineno = getattr(res, "lineno", None) if res else None
        runs = getattr(res, "suite_runs", None) if res else None
    except Exception as e:                        # noqa: BLE001
        import traceback
        err = traceback.format_exc(limit=6)
        status = rfile = reason = summary = None
        restored_original = new_line = old_line = lineno = runs = None
        greens = []
    secs = time.time() - t0

    got = open(mod, "rb").read()
    gmode = stat.S_IMODE(os.stat(mod).st_mode)
    post_green = None
    try:
        post_green = Oracle(d, python=PY, timeout=SUITE_TIMEOUT).green()
    except Exception:                             # noqa: BLE001
        pass

    return {
        "name": name, "note": fixture["note"], "seconds": round(secs, 1),
        "pre_green": pre_green, "post_green": post_green,
        "status": status, "file": rfile, "lineno": lineno, "suite_runs": runs,
        "reason": (reason or "")[:600], "summary": (summary or "")[:900],
        "restored_original": restored_original, "greens": (greens or [])[:6],
        "old_line": old_line, "new_line": new_line, "error": err,
        "byte_exact": got == pristine,
        "unchanged_from_defect": got == defect,
        "mode_pristine": oct(pmode), "mode_after": oct(gmode),
        "mode_preserved": pmode == gmode,
        "first_diff_offset": first_diff(pristine, got),
        "eol_pristine": eol_profile(pristine),
        "eol_after": eol_profile(got),
        "line_diff": line_diff(pristine, got)[:8],
    }


def main():
    want = sys.argv[1:]
    os.makedirs(WORK, exist_ok=True)
    rows = []
    for fixture in F:
        if want and not any(w in fixture["name"] for w in want):
            continue
        print(f"--- {fixture['name']} ...", flush=True)
        row = run_one(fixture)
        rows.append(row)
        verdict = ("BYTE-EXACT" if row.get("byte_exact") else
                   "NOT-BYTE-EXACT")
        print(f"    status={row.get('status')} {verdict} "
              f"mode_ok={row.get('mode_preserved')} "
              f"post_green={row.get('post_green')} "
              f"({row.get('seconds')}s)", flush=True)
        if row.get("line_diff"):
            for ld in row["line_diff"]:
                print(f"      L{ld['line']} pristine={ld['pristine']}",
                      flush=True)
                print(f"      L{ld['line']}  on_disk={ld['on_disk']}",
                      flush=True)
        if row.get("error"):
            print("      ERROR:\n" + row["error"], flush=True)
    with open(os.path.join(HERE, "results2.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    ok = sum(1 for r in rows if r.get("byte_exact"))
    rep = sum(1 for r in rows if r.get("status") == "repaired")
    print(f"\n== {rep} repaired / {len(rows)} fixtures; "
          f"{ok} byte-exact; results2.json written", flush=True)


if __name__ == "__main__":
    main()
