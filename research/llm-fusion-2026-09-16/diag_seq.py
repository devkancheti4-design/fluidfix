"""Same two cases as the harness, but through the CLI in a persisted tree: does case 2's
localisation still miss mod_195 when a previous guard run left its state behind?"""
import json, random, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import scale_localise as S
PY = sys.executable; ENV = {"PYTHONPATH": "/Users/kanchetidevieswar/neo/fluidfix/src", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
root = Path(tempfile.mkdtemp(prefix="diagseq-")) / "repo"; S.build(root, 300)
g = lambda *c: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *c], cwd=root, capture_output=True, text=True)
g("init", "-q", "-b", "main"); g("add", "-A"); g("commit", "-qm", "green")
picks = random.Random(20260916).sample(range(300), 10)
for j in (0, 1):
    i = picks[j]; pristine, defect, kind = S.SHAPES[j]; p = root / f"pkg/mod_{i:03d}.py"; src = p.read_text()
    g("checkout", "-q", "--", "."); p.write_text(src.replace(pristine, defect)); g("commit", "-qam", f"break {i}")
    r = subprocess.run([PY, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", "240"], cwd=root, capture_output=True, text=True, env=ENV)
    ref = root / ".fluidfix" / "last_refusal.json"
    cands = json.load(open(ref))["candidates"] if (r.returncode == 2 and ref.exists()) else None
    print(f"case {j+1} mod_{i:03d} {kind}: exit={r.returncode} exact={p.read_text()==src} searched={cands}", flush=True)
    print("   ", [l for l in r.stdout.splitlines() if "repaired" in l or "REFUSED" in l][:1])
print("tree leftovers:", sorted(x.name for x in root.iterdir() if x.name.startswith(".")))
