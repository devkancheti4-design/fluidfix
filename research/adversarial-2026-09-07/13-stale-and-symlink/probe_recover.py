"""Does the crash-recovery journal also write through a symlink, out of root?
Uses loop.recover_inflight() exactly as shipped."""
import json, os, shutil, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.loop import recover_inflight, begin_inflight

HERE = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(HERE, "fixtures", "f16-journal-escape")
shutil.rmtree(base, ignore_errors=True)
repo, out = os.path.join(base, "repo"), os.path.join(base, "outside")
os.makedirs(os.path.join(repo, "pkg")); os.makedirs(out)
open(os.path.join(out, "geom.py"), "w").write("REAL CONTENT, outside the root\n")
os.symlink(os.path.join("..", "..", "outside", "geom.py"),
           os.path.join(repo, "pkg", "geom.py"))
begin_inflight(repo, "pkg/geom.py", "JOURNAL RESTORE PAYLOAD\n")
print("journal:", open(os.path.join(repo, ".fluidfix", "inflight.json")).read())
print("recover_inflight ->", recover_inflight(repo))
print("outside file now:", repr(open(os.path.join(out, "geom.py")).read()))
print("repo/pkg/geom.py is still a symlink:", os.path.islink(os.path.join(repo, "pkg", "geom.py")))
