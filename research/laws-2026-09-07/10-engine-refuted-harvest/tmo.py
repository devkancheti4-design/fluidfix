#!/usr/bin/env python3
"""timeout(1) substitute for macOS (no coreutils here): tmo.py SECS cmd..."""
import os, signal, subprocess, sys
secs, cmd = int(sys.argv[1]), sys.argv[2:]
p = subprocess.Popen(cmd, start_new_session=True)
try:
    sys.exit(p.wait(timeout=secs))
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    print(f"[tmo] killed after {secs}s", file=sys.stderr)
    sys.exit(124)
