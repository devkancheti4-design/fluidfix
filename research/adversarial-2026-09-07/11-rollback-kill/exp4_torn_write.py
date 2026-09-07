"""Is _write atomic? It is open(path,'w')+f.write -> truncate THEN write. A
SIGKILL between truncate and flush should leave a SHORT/torn file. Try to catch
mod.py at a size that is neither pristine nor any full candidate (a partial)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kutil as K

# large victim: pad with a big module-level comment AFTER the function so every
# candidate rewrite is ~1.5MB and _write takes long enough to interrupt.
root = K.fresh_victim("v4")
mod = os.path.join(root, "mod.py")
base = open(mod).read()
pad = "\n" + ("# pad %06d ---------------------------------------------------------------\n" % 0) * 20000
open(mod, "w").write(base + pad)
O = K.read_bytes(mod)
full_len = len(O)
print("padded mod.py size:", full_len)

caught = None
for attempt in range(12):
    open(mod, "w").write(base + pad)   # reset to pristine large file
    p = K.launch(["repair", root, "--file", "mod.py", "--python", K.PY, "--cov", "mod"],
                 sleep=3, hardcap=60)
    # tight poll for a SHORT file (a torn write: 0 < size < full and content
    # is not a full line-swap candidate, i.e. size drifts from full_len by !=1)
    t0 = time.time(); hit = None
    path = mod
    while time.time() - t0 < 25 and p.poll() is None:
        try:
            sz = os.path.getsize(path)
        except OSError:
            sz = None
        if sz is not None and 0 <= sz < full_len - 4:   # clearly truncated (a full swap changes size by ~1)
            hit = sz
            K.killpg(p)
            break
        time.sleep(0.0005)
    if hit is None:
        K.killpg(p)
        K.verify_dead_and_stable(root, "mod.py", p, settle=0.3)
        continue
    exited, stable, cur = K.verify_dead_and_stable(root, "mod.py", p, settle=0.5)
    print(f"attempt {attempt}: caught size={hit} (full={full_len}); after-settle size={len(cur)} exited={exited} stable={stable}")
    if len(cur) < full_len - 4:
        caught = (hit, len(cur))
        # is the journal intact for recovery?
        import json
        jp = os.path.join(root, ".fluidfix", "inflight.json")
        rec = json.load(open(jp)) if os.path.exists(jp) else None
        print("  torn file left on disk. journal.original==pristine?",
              rec is not None and rec.get("original","").encode() == O)
        break

print("\nRESULT:", ("caught a TORN/truncated file on disk: " + str(caught)) if caught
      else "did not catch a partial write in 12 tries (window is sub-ms); "
           "_write remains non-atomic by construction (open 'w' truncates before write)")
K.killpg  # noop ref
ps = os.popen("ps -eo pid,command | grep -E '/v4|victim_template' | grep -v grep").read().strip()
print("lingering:", ps or "(none)")
