#!/usr/bin/env python3
"""Build the file-shape victim repos for target 13-stale-and-symlink.

Every fixture is the SAME one-line defect (kind 3, flipped-additive:
`a - b` where the suite pins `a + b`) in the SAME tiny package.  Only the
FILE SHAPE changes: line endings, trailing newline, BOM, permissions,
symlink, hardlink, mtime.  That isolates the file-writing path as the
independent variable — a fixture that fluidfix repairs in the plain shape
and refuses/corrupts in a shaped variant is a defect of the writing path,
not of the search.

Run:  python make_fixtures.py <outdir>
"""
import os
import shutil
import stat
import sys
import time

BODY_LINES = [
    "def add(a, b):",
    '    """The defect: the suite pins a + b."""',
    "    return a - b",
    "",
    "",
    "def scale(v, k):",
    "    return v * k",
    "",
]

TEST = """import pkg.geom as g


def test_add():
    assert g.add(2, 3) == 5


def test_scale():
    assert g.scale(2, 3) == 6
"""


def write(path, data: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def base_repo(root, geom_bytes, geom_at=None):
    """geom_at: where the real geom.py lives (default pkg/geom.py)."""
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    write(os.path.join(root, "pkg", "__init__.py"), b"")
    write(os.path.join(root, "tests", "test_geom.py"), TEST.encode())
    write(os.path.join(root, "pyproject.toml"),
          b"[tool.pytest.ini_options]\npythonpath = ['.']\n")
    target = geom_at or os.path.join(root, "pkg", "geom.py")
    write(target, geom_bytes)
    return target


LF = ("\n".join(BODY_LINES)).encode()                   # ends with "\n"
NO_EOL = ("\n".join(BODY_LINES).rstrip("\n")).encode()  # no trailing newline
CRLF = ("\r\n".join(BODY_LINES)).encode()
BOM = b"\xef\xbb\xbf" + LF
LATIN1 = ("\n".join(
    ["# -*- coding: latin-1 -*-", "SYMBOL = '\xa9 caf\xe9'"] + BODY_LINES
)).encode("latin-1")


def build(outdir):
    made = {}

    # 1. control — plain LF, ordinary file
    r = os.path.join(outdir, "f01-plain"); base_repo(r, LF); made["f01-plain"] = r

    # 2. no trailing newline
    r = os.path.join(outdir, "f02-no-eol"); base_repo(r, NO_EOL); made["f02-no-eol"] = r

    # 3. CRLF throughout
    r = os.path.join(outdir, "f03-crlf"); base_repo(r, CRLF); made["f03-crlf"] = r

    # 4. UTF-8 BOM (what a Windows editor leaves behind; CPython imports it fine)
    r = os.path.join(outdir, "f04-bom"); base_repo(r, BOM); made["f04-bom"] = r

    # 5. read-only source file (0o444), writable directory
    r = os.path.join(outdir, "f05-readonly"); t = base_repo(r, LF)
    os.chmod(t, 0o444); made["f05-readonly"] = r

    # 6. odd but legal mode: setgid-ish / group-writable / executable source
    r = os.path.join(outdir, "f06-mode755"); t = base_repo(r, LF)
    os.chmod(t, 0o755); made["f06-mode755"] = r

    # 7. hardlink: pkg/geom.py and vendor/geom_hardlink.py are ONE inode
    r = os.path.join(outdir, "f07-hardlink"); t = base_repo(r, LF)
    os.makedirs(os.path.join(r, "vendor"), exist_ok=True)
    os.link(t, os.path.join(r, "vendor", "geom_hardlink.py"))
    made["f07-hardlink"] = r

    # 8. symlink INSIDE the root: pkg/geom.py -> ../real/geom.py
    r = os.path.join(outdir, "f08-symlink-in"); base_repo(r, LF)
    os.remove(os.path.join(r, "pkg", "geom.py"))
    write(os.path.join(r, "real", "geom.py"), LF)
    os.symlink(os.path.join("..", "real", "geom.py"),
               os.path.join(r, "pkg", "geom.py"))
    made["f08-symlink-in"] = r

    # 9. symlink OUT of the root: pkg/geom.py -> <outdir>/f09-outside/geom.py
    #    The repo fluidfix is pointed at is f09-symlink-out/repo; the real
    #    source lives in a sibling directory it was never given.
    r = os.path.join(outdir, "f09-symlink-out")
    shutil.rmtree(r, ignore_errors=True)
    repo = os.path.join(r, "repo")
    outside = os.path.join(r, "outside")
    base_repo(repo, LF)
    os.remove(os.path.join(repo, "pkg", "geom.py"))
    write(os.path.join(outside, "geom.py"), LF)
    os.symlink(os.path.join("..", "..", "outside", "geom.py"),
               os.path.join(repo, "pkg", "geom.py"))
    made["f09-symlink-out"] = repo

    # 10. future mtime on an UNRELATED source file (a vendored .c with a bad
    #     timestamp) — the C-guard staleness probe's input
    r = os.path.join(outdir, "f10-future-mtime"); base_repo(r, LF)
    write(os.path.join(r, "vendor", "third_party.c"), b"int unused(void){return 0;}\n")
    fut = time.time() + 3600 * 24 * 365
    os.utime(os.path.join(r, "vendor", "third_party.c"), (fut, fut))
    made["f10-future-mtime"] = r

    # 11. mixed endings: CRLF file with one lone-LF line and one lone-CR line
    mixed = (b"def add(a, b):\r\n"
             b"    # a lone CR line ending follows on the next line\r\n"
             b"    return a - b\r\n"
             b"\r\n"
             b"\r\n"
             b"def scale(v, k):\n"          # lone LF inside a CRLF file
             b"    return v * k\r\n")
    r = os.path.join(outdir, "f11-mixed-eol"); base_repo(r, mixed)
    made["f11-mixed-eol"] = r

    # 12. latin-1 declared source (legal Python, PEP 263), not valid UTF-8
    r = os.path.join(outdir, "f12-latin1"); base_repo(r, LATIN1)
    made["f12-latin1"] = r

    return made


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, root in build(out).items():
        print(f"{name}\t{root}")
