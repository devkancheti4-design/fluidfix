"""Why was pkg/mod_195.py not among the candidates? Rebuild the same repo, inject the same
defect, and print the file ranking with the evidence the SIGHT law was given."""
import json, random, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src"); sys.path.insert(0, str(Path(__file__).parent))
import scale_localise as S
from fluidfix import Oracle
from fluidfix.guard import find_candidate_files
root = Path(tempfile.mkdtemp(prefix="diag-")) / "repo"; S.build(root, 300)
picks = random.Random(20260916).sample(range(300), 10); i = picks[1]; print("picked", i)
pristine, defect, kind = S.SHAPES[1]; p = root / f"pkg/mod_{i:03d}.py"; p.write_text(p.read_text().replace(pristine, defect))
o = Oracle(str(root), python=sys.executable)
red, out = o.failing_output(); print("red:", red); print("\n".join(l for l in out.splitlines() if "FAIL" in l or "assert" in l)[:600])
ev = {}
ranked = find_candidate_files(o, out, limit=10, evidence=ev)
print("ranked:", ranked)
print("true file rank:", ranked.index(f"pkg/mod_{i:03d}.py") + 1 if f"pkg/mod_{i:03d}.py" in ranked else None)
print("evidence:", json.dumps(ev, default=str)[:1500])
