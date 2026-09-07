"""End-to-end CLI reproduction of the two byte-exactness findings, in a git
repo so `restored_original` (fluidfix's own byte-exactness bit) is defined.

    ./rt 600 ../../../.venv/bin/python repro_cli.py

Builds two throwaway repos under work/cli-*, commits the PRISTINE file,
writes the defect as an uncommitted edit, then runs the real
`fluidfix guard` binary and diffs the result against `git show HEAD:mod.py`.
Only `git init/add/commit` inside work/ — never against the fluidfix repo.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
FLUIDFIX = os.path.join(ROOT, ".venv", "bin", "fluidfix")
PY = os.path.join(ROOT, ".venv", "bin", "python")
RT = os.path.join(HERE, "rt")

CASES = {
    # name: (pristine, defect, test)
    "cli-03-trailing-ws": (
        "def join2(a, b):\n    return a + b  \n",
        "def join2(a, b):\n    return b + a  \n",
        "from mod import join2\n\ndef test_j():\n"
        "    assert join2('x', 'y') == 'xy'\n"),
    "cli-19-comment": (
        "def delta(a, b):\n    return a - b  # signed difference\n",
        "def delta(a, b):\n    return b - a  # signed difference\n",
        "from mod import delta\n\ndef test_zero_b():\n"
        "    assert delta(5, 0) == 5\n"),
}


def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


for name, (pristine, defect, test) in CASES.items():
    d = os.path.join(HERE, "work", name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    open(os.path.join(d, "mod.py"), "w", newline="").write(pristine)
    open(os.path.join(d, "test_mod.py"), "w", newline="").write(test)
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "audit@local"],
                ["git", "config", "user.name", "audit"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "pristine (correct) source"]):
        sh(cmd, d)
    open(os.path.join(d, "mod.py"), "w", newline="").write(defect)

    print("=" * 72)
    print(f"### {name}")
    p = sh([RT, "300", FLUIDFIX, "guard", d, "--python", PY,
            "--suite-timeout", "45"], d)
    print(p.stdout.strip() or p.stderr.strip())
    got = open(os.path.join(d, "mod.py"), "rb").read()
    head = sh(["git", "show", "HEAD:mod.py"], d).stdout.encode()
    print(f"\n  bytes on disk : {got!r}")
    print(f"  pristine HEAD : {head!r}")
    print(f"  BYTE-EXACT    : {got == head}")
    print(f"  git diff      :\n{sh(['git', 'diff', '--stat'], d).stdout}")
    print(sh(["git", "--no-pager", "diff", "-U0", "--", "mod.py"], d).stdout)
