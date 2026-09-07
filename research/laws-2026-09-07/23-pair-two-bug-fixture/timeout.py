#!/usr/bin/env python3
"""timeout(1) substitute: this macOS box has no coreutils `timeout`/`gtimeout`
(verified: `which gtimeout timeout` -> not found). Usage:

    nice -n 15 python timeout.py <seconds> -- <command> [args...]

Kills the whole process group on expiry and exits 124, like GNU timeout.
"""
import os
import signal
import subprocess
import sys

secs = float(sys.argv[1])
argv = sys.argv[2:]
if argv and argv[0] == "--":
    argv = argv[1:]
p = subprocess.Popen(argv, start_new_session=True)
try:
    sys.exit(p.wait(timeout=secs))
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    p.wait()
    sys.stderr.write(f"timeout.py: killed after {secs}s\n")
    sys.exit(124)
