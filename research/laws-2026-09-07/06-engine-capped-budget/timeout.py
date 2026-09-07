#!/usr/bin/env python
"""macOS has no coreutils `timeout`; this is the brief's `timeout 300` wrapper.
usage: timeout.py <seconds> <cmd> [args...]  — kills the whole process group
on expiry and exits 124, like GNU timeout."""
import os, signal, subprocess, sys, time
secs = float(sys.argv[1]); cmd = sys.argv[2:]
p = subprocess.Popen(cmd, start_new_session=True)
try:
    rc = p.wait(timeout=secs)
except subprocess.TimeoutExpired:
    print(f"[timeout.py] {secs:.0f}s expired — killing process group", flush=True)
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    p.wait()
    sys.exit(124)
sys.exit(rc)
