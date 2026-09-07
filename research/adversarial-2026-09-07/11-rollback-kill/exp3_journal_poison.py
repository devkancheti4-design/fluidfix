"""Double-fault: kill under `repair`, do the natural `repair` retry, get killed
again. Show the crash journal now holds a MUTATION as 'original', so the
SANCTIONED recovery (recover_inflight, i.e. what guard/cguard run on startup)
restores the repo to a broken state the user never had."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kutil as K

root = K.fresh_victim("v3")
mod = os.path.join(root, "mod.py")
O = K.read_bytes(mod)
M0 = K.manifest(root)
jp = os.path.join(root, ".fluidfix", "inflight.json")

def kill_mid_candidate(baseline, label):
    p = K.launch(["repair", root, "--file", "mod.py", "--python", K.PY, "--cov", "mod"],
                 sleep=8, hardcap=90)
    status, _ = K.wait_for_mutation(root, "mod.py", baseline, p, timeout=40)
    if status != "mutated":
        print(f"[{label}] did not catch a mutation ({status})"); print(p.communicate()[0][:1500]); sys.exit(1)
    K.killpg(p)
    exited, stable, cur = K.verify_dead_and_stable(root, "mod.py", p)
    assert exited and stable, f"[{label}] kill not clean"
    rec = json.load(open(jp)) if os.path.exists(jp) else None
    print(f"[{label}] leftover on disk: {cur.decode()!r}")
    print(f"[{label}] journal.original == pristine O? {rec and rec.get('original','').encode()==O}")
    return cur, rec

print("KILL #1 (fresh repair on pristine):")
L1, rec1 = kill_mid_candidate(O, "kill1")

print("\nNATURAL RETRY: `fluidfix repair` again, KILL #2 mid-candidate:")
L2, rec2 = kill_mid_candidate(L1, "kill2")
poisoned = rec2 and rec2.get("original","").encode()
print("journal.original now == pristine O? ", poisoned == O)
print("journal.original now == leftover L1?", poisoned == L1)

print("\nUSER RUNS THE SANCTIONED RECOVERY (recover_inflight == guard/cguard startup):")
import subprocess
subprocess.run(["/bin/bash", K.RUNLIM, "30", K.PY, "-c",
    "from fluidfix.loop import recover_inflight; recover_inflight(%r)" % root], check=True)
final = K.read_bytes(mod)
print("recovered mod.py == pristine O ?", final == O)
print("recovered mod.py == leftover L1?", final == L1)
print("recovered mod.py bytes:", final.decode())

print("=== FINAL MANIFEST DIFF vs pristine ===")
for line in K.diff_manifest(M0, K.manifest(root)):
    print(line)
print("\nVERDICT:", "CORRUPTION via the sanctioned recovery path — repo restored to a broken variant"
      if final != O else "recovery reached pristine")
