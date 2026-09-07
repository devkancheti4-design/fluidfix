"""E1: four escape shapes against coracle.py's killpg defence.

Shapes (all realistic in a C/C++ test harness):
  A plain-grandchild   test binary forks a helper in the same group   -> should DIE
  B setsid-grandchild  helper calls setsid() (any daemon/server does) -> ?
  C double-fork        classic daemonize                              -> ?
  D no-timeout-leak    command EXITS 0 fast but leaves a background
                       process behind (a ctest fixture starting a
                       server). killpg only fires on TimeoutExpired.  -> ?
Helpers carry FFX14MARKER and self-exit after MAXLIFE seconds.
"""
import os, signal, subprocess, sys, time

MARK, MAXLIFE, PY = "FFX14MARKER", 40, sys.executable
SLEEP = f'import time;time.sleep({MAXLIFE})  # {MARK}'

def helper(pre=""):
    return f'{PY} -c "{pre}{SLEEP}" &'

SHAPES = {
 "A plain-grandchild ": f'sh -c \'{PY} -c "{SLEEP}" & sleep {MAXLIFE}\'',
 "B setsid-grandchild": f'sh -c \'{PY} -c "import os;os.setsid();{SLEEP}" & sleep {MAXLIFE}\'',
 "C double-fork      ": f'sh -c \'{PY} -c "import os,sys;\nif os.fork():sys.exit()\nos.setsid()\nif os.fork():os._exit(0)\n{SLEEP}" ; sleep {MAXLIFE}\'',
 "D no-timeout-leak  ": f'sh -c \'{PY} -c "{SLEEP}" & echo built-and-tested-ok; exit 0\'',
}

def alive():
    out = subprocess.run(["ps","-axo","pid=,pgid=,sess=,command="],
                         capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines()
            if MARK in l and "ps -axo" not in l and "probe_cpath" not in l]

def sweep():
    for _ in range(3):
        v = alive()
        if not v: return
        for l in v:
            try: os.kill(int(l.split()[0]), signal.SIGKILL)
            except OSError: pass
        time.sleep(0.5)

def csh(cmd, timeout):
    """verbatim coracle.py:189-207"""
    proc = None
    try:
        proc = subprocess.Popen(cmd, shell=True, text=True, errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True)
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out or ""
    except subprocess.TimeoutExpired:
        if proc is not None:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError): proc.kill()
            try: proc.communicate(timeout=10)
            except Exception: pass
        return 1, "TIMEOUT"

for name, cmd in SHAPES.items():
    sweep()
    t0 = time.time()
    rc, out = csh(cmd, 4)
    el = time.time() - t0
    time.sleep(1.0)
    surv = alive()
    verdict = "ESCAPED killpg" if surv else "reaped"
    print(f"{name}  rc={rc} {out.strip()[:24]!r:28} {el:5.1f}s  survivors={len(surv)}  -> {verdict}")
    for l in surv: print("      LEAKED pid/pgid/sess:", " ".join(l.split()[:3]))
    sweep()
print("final sweep survivors:", len(alive()))
