import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kutil as K

root = K.fresh_victim("v1")
mod = os.path.join(root, "mod.py")
O = K.read_bytes(mod)                      # pristine (broken) bytes
M0 = K.manifest(root)
print("pristine mod.py sha:", K.sha(mod))

p = K.launch(["repair", root, "--file", "mod.py", "--python", K.PY, "--cov", "mod"],
             sleep=8, hardcap=90)
status, leftover = K.wait_for_mutation(root, "mod.py", O, p, timeout=40)
print("wait_for_mutation ->", status)
if status == "mutated":
    K.killpg(p)
    exited, stable, _b = K.verify_dead_and_stable(root, "mod.py", p)
    print("SIGKILLed process group the instant a candidate hit disk.")
    print(f"post-kill: process exited={exited}  file-stable-after-settle={stable}")
    assert exited and stable, "KILL DID NOT FULLY STOP THE RUN -- methodology invalid"
else:
    print("process exited/timed out before we caught a mutation; output follows")
    print(p.communicate()[0][:2000])
    sys.exit(0)

# ---- disk state immediately after the kill (NO recovery run yet) ----
L = K.read_bytes(mod)
print("\n=== IMMEDIATELY AFTER SIGKILL (no recovery run) ===")
print("mod.py == pristine? ", L == O)
print("mod.py now reads:\n" + L.decode("utf-8", "replace"))
jp = os.path.join(root, ".fluidfix", "inflight.json")
print("journal exists? ", os.path.exists(jp))
if os.path.exists(jp):
    try:
        rec = json.load(open(jp))
        print("journal.file      =", rec.get("file"))
        print("journal.original == pristine? ", rec.get("original", "").encode() == O)
    except Exception as e:
        print("journal is CORRUPT/unparseable:", e)

M1 = K.manifest(root)
print("\n=== MANIFEST DIFF vs pristine (this is the repo the user is left with) ===")
for line in K.diff_manifest(M0, M1):
    print(line)

# save O for downstream experiments
open(os.path.join(K.HERE, "_v1_pristine.bytes"), "wb").write(O)
print("\n(leftover greenness is evaluated in the next step)")
