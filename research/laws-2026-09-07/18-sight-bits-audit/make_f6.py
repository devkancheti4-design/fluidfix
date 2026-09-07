#!/usr/bin/env python
"""Build the TOUCHED frame-of-reference pair.

TOUCHED is measured at guard.py:302-308 as

    recent_files = {l.strip() for l in
                    git -C <oracle.root> log -40 --name-only --format=
                    if l.strip().endswith(".py")}
    ...
    touched = rel in recent_files          # guard.py:286

`git log --name-only` prints paths relative to the REPOSITORY root, while
`rel` is relative to `oracle.root`. The two agree only when the project root
IS the repository root.

f6a_repo_root   project root == repo root      -> paths agree
f6b_subdir      project root == repo/proj      -> git prints "proj/mod.py",
                the body compares it against "mod.py"

Identical sources, identical git history, one commit touching mod.py. Any
difference in the TOUCHED bit is caused by the frame-of-reference mismatch
and nothing else.

This creates two brand-new throwaway git repositories INSIDE this agent's
own fixtures directory. No existing repository is touched.

Usage:  .venv/bin/python make_f6.py
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

MOD = ("def count_above(xs, t):\n"
       "    n = 0\n"
       "    for x in xs:\n"
       "        if x >= t:\n"          # defect: should be >
       "            n += 1\n"
       "    return n\n")
TEST = ("from mod import count_above\n"
        "\n"
        "def test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")

GIT_ENV = dict(os.environ,
               GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="f@x",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="f@x")


def build(name, subdir):
    repo = os.path.join(FIX, name)
    if os.path.isdir(repo):
        shutil.rmtree(repo)
    proj = os.path.join(repo, subdir) if subdir else repo
    os.makedirs(proj)
    open(os.path.join(proj, "pytest.ini"), "w").write("[pytest]\n")
    open(os.path.join(proj, "mod.py"), "w").write(MOD)
    open(os.path.join(proj, "test_mod.py"), "w").write(TEST)
    for args in (["init", "-q"], ["add", "-A"],
                 ["commit", "-q", "-m", "seed"]):
        subprocess.run(["git", "-C", repo] + args, check=True, env=GIT_ENV,
                       capture_output=True)
    out = subprocess.run(["git", "-C", proj, "log", "-40", "--name-only",
                          "--format="], capture_output=True, text=True).stdout
    print(f"{name}: project root = {proj}")
    print(f"   git -C <project root> log --name-only -> "
          f"{[l for l in out.split() if l.endswith('.py')]}")
    return proj


if __name__ == "__main__":
    build("f6a_repo_root", "")
    build("f6b_subdir", "proj")
