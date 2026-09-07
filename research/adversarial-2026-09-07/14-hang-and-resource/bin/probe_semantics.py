"""E0: what does each oracle's kill actually reap?

Reproduces, out of tree, the exact call shapes used by fluidfix:
  oracle.py:157      subprocess.run(cmd, timeout=T)                  (Python path)
  javaoracle.py:53   subprocess.run(cmd, timeout=T)                  (Java path)
  coracle.py:191     Popen(shell=True, start_new_session=True) + killpg  (C path)

Every helper is a python sleeper carrying the marker FFX14MARKER in argv and
self-exiting after MAXLIFE seconds, so nothing can outlive the experiment.
"""
import os, signal, subprocess, sys, time

MARK = "FFX14MARKER"
MAXLIFE = 40
PY = sys.executable

# a "test" that spawns ONE grandchild sleeper and then hangs itself
CHILD_SRC = f"""
import subprocess, sys, time
subprocess.Popen([sys.executable, "-c",
                  "import time;time.sleep({MAXLIFE})  # {MARK}-grandchild"])
time.sleep({MAXLIFE})   # {MARK}-child hangs, like a hung candidate
"""

def alive():
    out = subprocess.run(["ps", "-axo", "pid=,pgid=,command="],
                         capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines()
            if MARK in l and "ps -axo" not in l and "probe_semantics" not in l]

def sweep():
    for l in alive():
        try: os.kill(int(l.split()[0]), signal.SIGKILL)
        except OSError: pass
    time.sleep(0.5)

def shape_python_oracle():
    """exact shape of oracle.py:157 / javaoracle.py:53"""
    try:
        subprocess.run([PY, "-c", CHILD_SRC], capture_output=True, timeout=3)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    return "exited"

def shape_c_oracle():
    """exact shape of coracle.py:191-207"""
    proc = None
    try:
        proc = subprocess.Popen(f'{PY} -c \'{CHILD_SRC}\'', shell=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True)
        proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError): proc.kill()
        try: proc.communicate(timeout=10)
        except Exception: pass
        return "TIMEOUT"
    return "exited"

for name, fn in (("oracle.py:157 / javaoracle.py:53  subprocess.run(timeout=)", shape_python_oracle),
                 ("coracle.py:191  Popen(start_new_session)+killpg", shape_c_oracle)):
    sweep()
    r = fn()
    time.sleep(1.0)
    surv = alive()
    print(f"\n--- {name}")
    print(f"    result={r}  survivors_after_kill={len(surv)}")
    for l in surv:
        print("      LEAKED:", l[:110])
    sweep()

print("\nfinal sweep, survivors:", len(alive()))
