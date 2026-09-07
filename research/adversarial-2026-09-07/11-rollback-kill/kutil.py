"""Kill-harness utilities for target 11-rollback-kill.

Everything runs the fluidfix binary through runlim.sh (nice -n 15 + perl-alarm
hard cap) in a fresh session (start_new_session) so we own the process group and
kill ONLY what we started. No fluidfix source is touched.
"""
import hashlib
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNLIM = os.path.join(HERE, "runlim.sh")
FLUIDFIX = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix"
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
TEMPLATE = os.path.join(HERE, "victim_template")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root):
    """Every file under root: relpath -> (sha256, octal mode, size). Also the
    set of directories. This is what 'byte-identical + modes' is checked on."""
    files = {}
    dirs = set()
    for dp, dns, fns in os.walk(root):
        for d in dns:
            dirs.add(os.path.relpath(os.path.join(dp, d), root))
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            if os.path.islink(p):
                files[rel] = ("SYMLINK->" + os.readlink(p), oct(st.st_mode), st.st_size)
            else:
                files[rel] = (sha(p), oct(st.st_mode), st.st_size)
    return files, dirs


def diff_manifest(a, b):
    """a=pristine, b=after. Returns list of human-readable differences."""
    fa, da = a
    fb, db = b
    out = []
    for rel in sorted(set(fa) | set(fb)):
        va, vb = fa.get(rel), fb.get(rel)
        if va is None:
            out.append(f"  ADDED   {rel}  mode={vb[1]} size={vb[2]} sha={vb[0][:12]}")
        elif vb is None:
            out.append(f"  REMOVED {rel}")
        elif va[0] != vb[0]:
            out.append(f"  CONTENT {rel}  {va[0][:12]} -> {vb[0][:12]} (size {va[2]}->{vb[2]})")
        elif va[1] != vb[1]:
            out.append(f"  MODE    {rel}  {va[1]} -> {vb[1]}")
    for rel in sorted(db - da):
        out.append(f"  DIR+    {rel}")
    for rel in sorted(da - db):
        out.append(f"  DIR-    {rel}")
    return out


def fresh_victim(name, sleep="0"):
    dst = os.path.join(HERE, name)
    subprocess.run(["rm", "-rf", dst], check=True)
    subprocess.run(["cp", "-R", TEMPLATE, dst], check=True)
    return dst


def launch(cmd_args, sleep, hardcap=90):
    """Launch fluidfix through runlim in a new session. Returns Popen.
    cmd_args: list after the fluidfix binary, e.g. ['repair', root, '--file','mod.py',...]"""
    env = dict(os.environ, VICTIM_SLEEP=str(sleep))
    full = ["/bin/bash", RUNLIM, str(hardcap), FLUIDFIX] + cmd_args
    return subprocess.Popen(full, start_new_session=True, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)


def killpg(p):
    """SIGKILL the whole session group we started (perl + fluidfix + pytest),
    then reap. Kills ONLY the group we launched with start_new_session."""
    try:
        pgid = os.getpgid(p.pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        p.wait(timeout=5)
    except Exception:
        pass


def verify_dead_and_stable(root, rel, p, settle=1.5):
    """After a kill, confirm the process is gone and the target file has stopped
    changing (no surviving mutator). Returns (exited_bool, stable_bool, bytes)."""
    exited = p.poll() is not None
    a = read_bytes(os.path.join(root, rel))
    time.sleep(settle)
    b = read_bytes(os.path.join(root, rel))
    return exited, (a == b), b


def wait_for_mutation(root, rel, pristine_bytes, p, timeout=40, poll=0.02):
    """Poll the target file; return ('mutated', bytes) the instant it differs
    from pristine (a candidate is applied on disk), or ('exited', None) if the
    process finished first, or ('timeout', None)."""
    path = os.path.join(root, rel)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if p.poll() is not None:
            return ("exited", None)
        try:
            with open(path, "rb") as f:
                cur = f.read()
        except OSError:
            cur = None
        if cur is not None and cur != pristine_bytes:
            return ("mutated", cur)
        time.sleep(poll)
    return ("timeout", None)


def read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None
