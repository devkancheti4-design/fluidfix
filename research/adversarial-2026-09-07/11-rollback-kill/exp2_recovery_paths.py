import json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kutil as K

v1 = os.path.join(K.HERE, "v1")
O = open(os.path.join(K.HERE, "_v1_pristine.bytes"), "rb").read()
mod_v1 = os.path.join(v1, "mod.py")
assert K.read_bytes(mod_v1) != O, "v1 must be in the killed (mutated) state"
L1 = K.read_bytes(mod_v1)
print("killed-state mod.py (leftover L1):", repr(L1.decode()))

def suite_red(root):
    r = subprocess.run([K.PY, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
                       cwd=root, capture_output=True, text=True,
                       env=dict(os.environ, VICTIM_SLEEP="0", PYTHONDONTWRITEBYTECODE="1"))
    return r.returncode != 0

print("leftover L1 suite RED?", suite_red(v1))   # confirm the leftover is a broken program

# ---------------------------------------------------------------------------
# PATH A (defense): what guard/cguard do on startup == recover_inflight().
# ---------------------------------------------------------------------------
va = os.path.join(K.HERE, "v1_guardrecover"); shutil.rmtree(va, ignore_errors=True); shutil.copytree(v1, va)
print("\n=== PATH A: recover_inflight (guard/cguard startup) ===")
out = subprocess.run(["/bin/bash", K.RUNLIM, "30", K.PY, "-c",
        "from fluidfix.loop import recover_inflight; print('restored:', recover_inflight(%r))" % va],
        capture_output=True, text=True)
print(out.stdout.strip(), out.stderr.strip())
modA = K.read_bytes(os.path.join(va, "mod.py"))
print("mod.py == pristine after recover?", modA == O)
print("journal removed?", not os.path.exists(os.path.join(va, ".fluidfix", "inflight.json")))

# ---------------------------------------------------------------------------
# PATH B (attack): the NATURAL retry -- `fluidfix repair` again. It does NOT
# call recover_inflight; it reads the leftover L1 as the user's source.
# ---------------------------------------------------------------------------
vb = os.path.join(K.HERE, "v1_repairagain"); shutil.rmtree(vb, ignore_errors=True); shutil.copytree(v1, vb)
jp = os.path.join(vb, ".fluidfix", "inflight.json")
rec0 = json.load(open(jp))
print("\n=== PATH B: `fluidfix repair` re-run (no recovery on this path) ===")
print("BEFORE retry: journal.original == pristine?", rec0.get("original", "").encode() == O)

p = K.launch(["repair", vb, "--file", "mod.py", "--python", K.PY, "--cov", "mod"],
             sleep=0, hardcap=90)
# let it run to completion this time (natural retry, no kill)
out2 = p.communicate(timeout=120)[0]
print("retry exit:", p.returncode)
print("retry says:", out2.strip().splitlines()[-1] if out2.strip() else "(no output)")

modB = K.read_bytes(os.path.join(vb, "mod.py"))
print("\nAFTER retry completes:")
print("  mod.py == pristine original O ?", modB == O)
print("  mod.py == leftover L1 ?        ", modB == L1)
print("  mod.py bytes:", repr(modB.decode()))
print("  journal still present?         ", os.path.exists(jp))
if os.path.exists(jp):
    recn = json.load(open(jp))
    print("  journal.original == pristine O?", recn.get("original","").encode() == O)
    print("  journal.original == leftover L1?", recn.get("original","").encode() == L1)
print("  -> Can the TRUE pristine original still be recovered from anywhere fluidfix wrote? "
      + ("NO" if (modB != O and not (os.path.exists(jp) and json.load(open(jp)).get('original','').encode()==O)) else "yes"))
