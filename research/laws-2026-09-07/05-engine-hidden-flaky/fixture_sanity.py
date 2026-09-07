"""Sanity: per-variant pytest green rate on each fixture, 20 runs each.
Run: nice -n 15 .venv/bin/python fixture_sanity.py
"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
VARIANTS = {"defect a - b": "    return a - b\n",
            "wrong  b - a": "    return b - a\n",
            "right  a + b": "    return a + b\n"}
N = 20
for fx in ("fixture_a", "fixture_b"):
    for name, line in VARIANTS.items():
        tmp = tempfile.mkdtemp(prefix="san_", dir=HERE)
        shutil.copytree(os.path.join(HERE, fx), tmp, dirs_exist_ok=True)
        with open(os.path.join(tmp, "calc.py"), "w") as f:
            f.write("def add(a, b):\n" + line)
        greens = 0
        for _ in range(N):
            p = subprocess.run([PY, "-m", "pytest", "-q", "--no-header", "-p",
                                "no:cacheprovider", "--tb=no"], cwd=tmp,
                               capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            greens += (p.returncode == 0)
        shutil.rmtree(tmp)
        print(f"{fx}  {name}: green {greens}/{N}")
