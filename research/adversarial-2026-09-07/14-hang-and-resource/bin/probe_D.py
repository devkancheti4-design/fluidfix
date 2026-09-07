"""E2: WHY does shape D escape? Instrument coracle's killpg branch."""
import os, signal, subprocess, sys, time
MARK, PY = "FFX14MARKER", sys.executable
cmd = f'{PY} -c "import time;time.sleep(40)  # {MARK}" & echo ok; exit 0'

def ps():
    o = subprocess.run(["ps","-axo","pid=,ppid=,pgid=,stat=,command="],
                       capture_output=True, text=True).stdout
    return [l.strip() for l in o.splitlines() if MARK in l and "ps -axo" not in l and "probe_D" not in l]

proc = subprocess.Popen(cmd, shell=True, text=True, errors="replace",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        start_new_session=True)
print("Popen shell pid =", proc.pid)
try:
    proc.communicate(timeout=4)
    print("communicate returned normally (no timeout)")
except subprocess.TimeoutExpired:
    print("TimeoutExpired raised -> entering coracle's kill branch")
    print("  poll() (None=running, int=already exited/zombie):", proc.poll())
    for l in ps(): print("  helper before kill:", " ".join(l.split()[:4]))
    try:
        pg = os.getpgid(proc.pid)
        print(f"  os.getpgid({proc.pid}) = {pg}  -> killpg({pg}, SIGKILL)")
        os.killpg(pg, signal.SIGKILL)
    except (OSError, ProcessLookupError) as e:
        print(f"  os.getpgid/killpg RAISED {type(e).__name__}: {e}")
        print("  -> FALLBACK proc.kill(): signals ONLY the shell pid, not the group")
        proc.kill()
    try: proc.communicate(timeout=10)
    except Exception as e: print("  second communicate:", type(e).__name__)
time.sleep(1)
surv = ps()
print("SURVIVORS:", len(surv))
for l in surv: print("  ", " ".join(l.split()[:4]))
for l in surv:
    try: os.kill(int(l.split()[0]), signal.SIGKILL)
    except OSError: pass
time.sleep(0.5); print("after sweep:", len(ps()))
