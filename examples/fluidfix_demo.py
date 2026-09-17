#!/usr/bin/env python3
"""fluidfix in five minutes, on one file of one real repository.

    python3 fluidfix_demo.py            # sets everything up in ./fluidfix-demo and runs

It clones Click (pinned commit), builds a virtualenv, installs `fluidfix` from PyPI, and then breaks
ONE line of src/click/shell_completion.py three times. Click's own test suite is the only judge.

  ACT 1  a fault fluidfix already knows      -> restores the exact original bytes, zero tokens
  ACT 2  a fault it does not know            -> refuses, and says why it refused
  ACT 3  one rule, written once, installed   -> repairs ACT 2's fault, zero tokens, for good

In production the rule in ACT 3 is what a model authors from the refusal report ACT 2 prints; it is
included here so the whole demo runs with no API key. The model never judges: the suite does.

Requires python3, git, and network access. Nothing is installed outside ./fluidfix-demo.
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CLICK_URL = "https://github.com/pallets/click"
CLICK_SHA = "6aabf099bfdd4c1e75fe8d0e0d4241372b988ab1"   # the commit these timings were measured on
TARGET = "src/click/shell_completion.py"
BUDGET = "300"

# (title, the line as it stands, the line after a developer's slip) — indentation comes from the file
ACT1 = ("a literal index, one off",
        "incomplete = split_arg_string(incomplete)[0]",
        "incomplete = split_arg_string(incomplete)[1]")
ACT2 = ("an emptiness guard, inverted",
        "if not value:",
        "if value:")

RULE = '''# rules_demo.py — ONE fault class, taught once, from ONE worked example.
#
#   if value:        <- shipped, and the empty case falls through to value[0]
#   if not value:    <- the fix
#
# In production a model writes this file from the refusal report and never judges it;
# fluidfix hands every candidate to your suite and rolls back byte-exact on rejection.

def _negate_bare_guard(line, o):
    m = re.match(r"^(\\s*)(if|elif|while) (\\w+):\\s*$", line)
    if not m:
        return [line]
    indent, keyword, name = m.groups()
    return [f"{indent}{keyword} not {name}:"]


register(4, "inverted-bare-guard",
         "a bare-name guard `if X:` that should read `if not X:`, so the empty case takes the wrong branch",
         re.compile(r"^\\s*(?:if|elif|while) \\w+:\\s*$"),
         _negate_bare_guard)
'''

BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"


def say(msg=""):
    print(msg, flush=True)


def banner(title, sub=""):
    say()
    say(f"{BOLD}{'=' * 78}{OFF}")
    say(f"{BOLD}  {title}{OFF}")
    if sub:
        say(f"{DIM}  {sub}{OFF}")
    say(f"{BOLD}{'=' * 78}{OFF}")


def run(cmd, cwd=None, env=None, timeout=1800, check=True, quiet=True):
    p = subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout,
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        say((p.stdout or "")[-2000:])
        say((p.stderr or "")[-2000:])
        raise SystemExit(f"failed: {' '.join(str(c) for c in cmd)}")
    if not quiet:
        say((p.stdout or "").rstrip())
    return p


def setup(root: Path) -> tuple[Path, str]:
    repo = root / "click"
    py = repo / ".venv" / "bin" / "python"
    ff = repo / ".venv" / "bin" / "fluidfix"
    if ff.exists():
        say(f"{DIM}  reusing {repo}{OFF}")
        return repo, str(ff)
    banner("SETUP", "clone Click, build a virtualenv, install fluidfix from PyPI (about two minutes)")
    repo.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], cwd=repo)
    run(["git", "remote", "add", "origin", CLICK_URL], cwd=repo, check=False)
    say("  fetching click ...")
    fetched = run(["git", "fetch", "-q", "--depth", "1", "origin", CLICK_SHA], cwd=repo, check=False)
    if fetched.returncode == 0:
        run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=repo)
    else:                                   # older git, or the pin is gone: take the current tip
        run(["git", "fetch", "-q", "--depth", "1", "origin", "HEAD"], cwd=repo)
        run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=repo)
        say(f"{DIM}  (pinned commit unavailable; using current main — line numbers may differ){OFF}")
    run(["git", "checkout", "-q", "-B", "demo"], cwd=repo)
    run(["git", "config", "user.email", "demo@fluidfix"], cwd=repo)
    run(["git", "config", "user.name", "fluidfix demo"], cwd=repo)
    say("  building the virtualenv ...")
    run([sys.executable, "-m", "venv", str(repo / ".venv")])
    pip = str(repo / ".venv" / "bin" / "pip")
    run([pip, "install", "-q", "--upgrade", "pip"])
    say("  installing click, pytest, pytest-cov, pytest-timeout, fluidfix ...")
    run([pip, "install", "-q", "-e", "."], cwd=repo)
    run([pip, "install", "-q", "pytest", "pytest-cov", "pytest-timeout", "fluidfix"], cwd=repo)
    v = run([str(repo / ".venv" / "bin" / "python"), "-c",
             "import fluidfix; print(fluidfix.__version__)"], cwd=repo).stdout.strip()
    say(f"  fluidfix {v} installed")
    return repo, str(ff)


def suite(repo: Path) -> tuple[bool, str]:
    py = str(repo / ".venv" / "bin" / "python")
    p = run([py, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
            cwd=repo, check=False, timeout=900)
    tail = [l for l in (p.stdout or "").splitlines() if l.strip()]
    return p.returncode == 0, (tail[-1] if tail else "")


def reset(repo: Path):
    run(["git", "reset", "-q", "--hard", "HEAD"], cwd=repo, check=False)
    run(["git", "clean", "-fdq", "-e", ".venv", "-e", "rules_demo.py"], cwd=repo, check=False)


def break_line(repo: Path, pristine: str, broken: str) -> tuple[int, str]:
    """Replace the one line whose code is `pristine` with `broken`, keeping the file's own indentation.
    Returns the line number and the original line verbatim — that is what a byte-exact repair must restore."""
    path = repo / TARGET
    lines = path.read_text(encoding="utf-8", newline="").split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == pristine]
    if len(hits) != 1:
        raise SystemExit(f"demo: {pristine!r} matches {len(hits)} lines in {TARGET} at this commit, expected 1")
    i = hits[0]
    original = lines[i]
    indent = original[: len(original) - len(original.lstrip())]
    lines[i] = indent + broken
    path.write_text("\n".join(lines), encoding="utf-8", newline="")
    run(["git", "commit", "-aqm", f"a developer breaks {TARGET}:{i + 1}"], cwd=repo)
    return i + 1, original


def guard(repo: Path, ff: str, dictionary: str | None = None):
    cmd = [ff, "guard", ".", "--commit", "--budget", BUDGET]
    if dictionary:
        cmd += ["--dictionary", dictionary]
    t0 = time.time()
    p = run(cmd, cwd=repo, check=False, timeout=3600)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out, round(time.time() - t0, 1)


def restored(repo: Path, original: str, lineno: int) -> bool:
    """Byte-exact: the line is the original line again, indentation and all."""
    line = (repo / TARGET).read_text(encoding="utf-8", newline="").split("\n")[lineno - 1]
    return line == original


def show(out: str, keep=("repaired line", "REFUSED", "  - ", "  + ", "committed", "hint:", "refusal report:")):
    for line in out.splitlines():
        if any(k in line for k in keep):
            say("    " + line.strip()[:200])


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "fluidfix-demo").resolve()
    repo, ff = setup(root)
    reset(repo)

    banner("BASELINE", "click's own suite, green, at the commit these timings were measured on")
    t0 = time.time()
    green, line = suite(repo)
    say(f"  {line}   {DIM}({round(time.time() - t0, 1)}s){OFF}")
    if not green:
        raise SystemExit("demo: the suite is not green at baseline; nothing to demonstrate")

    results = []

    # ---- ACT 1 ---------------------------------------------------------------
    banner("ACT 1 — a fault fluidfix already knows", ACT1[0])
    n, original = break_line(repo, ACT1[1], ACT1[2])
    say(f"  broke {TARGET}:{n}")
    say(f"{DIM}    - {ACT1[1]}{OFF}")
    say(f"{DIM}    + {ACT1[2]}{OFF}")
    say("  running: fluidfix guard . --commit --budget 300   (no model, no API key, no tokens)")
    code, out, dt = guard(repo, ff)
    show(out)
    ok = code == 0 and restored(repo, original, n)
    runs = (re.search(r"in (\d+) suite runs", out) or [None, "-"])[1]
    say(f"  {BOLD}{'byte-exact restore' if ok else 'NOT restored'}{OFF} in {dt}s over {runs} suite runs, 0 tokens")
    results.append(("ACT 1  known fault", "restored byte-exact" if ok else "not restored", dt, runs, "0"))
    reset(repo)

    # ---- ACT 2 ---------------------------------------------------------------
    banner("ACT 2 — a fault it does not know", ACT2[0])
    n, original = break_line(repo, ACT2[1], ACT2[2])
    say(f"  broke {TARGET}:{n}")
    say(f"{DIM}    - {ACT2[1]}{OFF}")
    say(f"{DIM}    + {ACT2[2]}{OFF}")
    say("  running: fluidfix guard . --commit --budget 300")
    code, out, dt = guard(repo, ff)
    show(out)
    refused = code != 0 and not restored(repo, original, n)
    say(f"  {BOLD}{'refused, and said why' if refused else 'did not refuse'}{OFF} after {dt}s")
    say(f"{DIM}  every candidate it tried is logged with the test that rejected it, in .fluidfix/last_refusal.json{OFF}")
    say(f"{DIM}  that report is the packet a model receives; the rule it writes back is ACT 3{OFF}")
    results.append(("ACT 2  unknown fault", "refused with reasons" if refused else "unexpected", dt, "-", "0"))

    # ---- ACT 3 ---------------------------------------------------------------
    banner("ACT 3 — one rule, taught once", "the same break, with the class installed")
    (repo / "rules_demo.py").write_text(RULE, encoding="utf-8")
    say("  wrote rules_demo.py:")
    for l in RULE.splitlines():
        if l.startswith("register(") or l.strip().startswith(("def _negate", "return [f")):
            say(f"{DIM}    {l.strip()[:96]}{OFF}")
    say("  running: fluidfix guard . --commit --budget 300 --dictionary rules_demo.py")
    code, out, dt = guard(repo, ff, "rules_demo.py")
    show(out)
    ok = code == 0 and restored(repo, original, n)
    runs = (re.search(r"in (\d+) suite runs", out) or [None, "-"])[1]
    say(f"  {BOLD}{'byte-exact restore' if ok else 'NOT restored'}{OFF} in {dt}s over {runs} suite runs, 0 tokens")
    say(f"{DIM}  the rule cost one model call, once. Every later member of this class costs nothing.{OFF}")
    results.append(("ACT 3  taught fault", "restored byte-exact" if ok else "not restored", dt, runs, "0"))
    reset(repo)

    # ---- summary -------------------------------------------------------------
    banner("SUMMARY", f"one file: {TARGET} · judge: click's own suite · {len(results)} acts")
    say(f"  {'act':22} {'outcome':22} {'seconds':>8} {'suite runs':>11} {'tokens':>7}")
    for a, o, d, r, tk in results:
        say(f"  {a:22} {o:22} {d:>8} {str(r):>11} {tk:>7}")
    say()
    say("  What makes a demo repo legible: a green suite under about five seconds, a defect file")
    say("  under about a thousand lines, and a failing test whose traceback names the source file.")
    say("  Where it refuses instead: faults in six-thousand-line data tables, and failures that name")
    say("  only a docstring. Those refusals are reported, never guessed at.")
    say()
    say(f"  the demo repository is left at {repo} — break another line and run the guard yourself")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\ninterrupted")
