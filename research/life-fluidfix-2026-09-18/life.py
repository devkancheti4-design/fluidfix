# Vendored from https://github.com/devkancheti4-design/life-debugger (life.py), AGPL-3.0, same
# author and licence as fluidfix. Unmodified: the recursive experiments here use it as the memory
# organ at every level of the fan-out — a guard remembers, the judge above it remembers, and a judge
# over judges would remember the same way. recall() on an absent key returns None, which is exactly
# the abstention fluidfix's laws already prefer over a guess.
#!/usr/bin/env python3
"""Life — exact, permanent, honest memory for any LLM.

One file. Python 3.8+. Zero dependencies. The memory is a local JSON file.

Why this exists: a gradient-trained LLM cannot give you exact, permanent,
honest recall — not as a missing feature, but as a measured consequence of
how it is trained (see proof/PROOF.md, reproducible in ~2 minutes).
The Life is the complementary organ: exact where the model is fuzzy,
permanent where the model forgets, and it says ABSTAIN where the model
would confidently guess.

What it is NOT (read HONEST LIMITS in README.md): it is exact-key only.
It cannot answer a paraphrase, it does not generalize, it does not reason.
Pair it with your model (reasoning) and, if you need fuzzy search, RAG.

CLI:
  python3 life.py put  KEY VALUE     store / revise a fact (newest wins)
  python3 life.py get  KEY           exact recall — value (exit 0) or ABSTAIN (exit 3)
  python3 life.py history KEY        full revision history with counts
  python3 life.py link A B           relate two keys (A -> B)
  python3 life.py chain KEY          follow relations multi-hop
  python3 life.py forget KEY         delete a key (exit 3 if it was absent)
  python3 life.py stats              keys, disk bytes, identity sha
  python3 life.py sha                identity hash (byte-exact twins match)
  python3 life.py doctor             is the Life fused & working HERE? (checklist)

The database file is ./life.json (override: --db PATH or env LIFE_DB).

Performance honesty: recall() in-process is ~1 microsecond [HW]. The CLI
round-trip is ~30-100 ms — interpreter start + whole-file load — and every
CLI write rewrites the whole file (O(N)). At large stores, use the Life
class in-process; the CLI is the zero-integration path, not the fast path.
"""
import json
import hashlib
import os
import sys

__version__ = "1.0.2"


class Life:
    """Recency-dominant exact-key count table with confidence-gated fusion.

    store: {key(str): {value(str): count(int)}}
    - learn() never overwrites: a revision ADDS a count larger than the sum
      of all previous counts, so the newest value always wins recall while
      the full history stays inspectable. A plain dict destroys history.
    - recall() on an absent key returns None — structural abstention.
      There is no similarity, no smoothing, no guess. Absence is knowable.
    - blend() folds the table into a model's output distribution with a
      confidence gate w = t/(t+C): unseen keys leave the model untouched,
      well-attested keys override it. This is the fusion organ — the one
      thing here a dict fundamentally does not have.
    - dumps()/sha(): canonical serialization. Two Lives fed the same stream
      are byte-identical; the sha survives save -> process death -> load.
    """

    C = 0.25  # confidence half-count for blend(): w = t / (t + C)

    def __init__(self, path=None):
        self.store = {}
        self.path = path
        if path and os.path.exists(path):
            self.load(path)

    # ------------------------------------------------------------- core
    def learn(self, key, value):
        """Store or revise. Recency-dominant: the new value's count exceeds
        the sum of everything before it, so it wins recall deterministically
        — while every earlier value stays in the table (see history)."""
        key, value = str(key).strip(), str(value)
        d = self.store.setdefault(key, {})
        t = sum(d.values())
        d[value] = d.get(value, 0) + t + 1
        return value

    def recall(self, key):
        """Exact recall. Returns the current value, or None (= ABSTAIN).
        No fuzzy match, no guess: an absent key is reported as absent."""
        d = self.store.get(str(key).strip())
        if not d:
            return None
        return max(d, key=d.get)  # counts are strictly dominant -> unique

    def history(self, key):
        """Full revision history [(value, count)], current value last."""
        d = self.store.get(str(key).strip(), {})
        return sorted(d.items(), key=lambda kv: kv[1])

    def forget(self, key):
        return self.store.pop(str(key).strip(), None)

    # -------------------------------------------------------- relations
    REL = "::relates_to"

    def link(self, a, b):
        """Relate a -> b. Retrieval-only edges: chain() walks them."""
        self.learn(str(a).strip() + self.REL, str(b).strip())

    def chain(self, start, max_hops=32):
        """Spreading-activation retrieval: follow relates_to edges.
        Multi-hop RETRIEVAL (a flat dict.get returns one value and knows
        no relations). Note: retrieval, not computation."""
        seen = [str(start).strip()]
        while len(seen) <= max_hops:
            nxt = self.recall(seen[-1] + self.REL)
            if nxt is None or nxt in seen:
                break
            seen.append(nxt)
        return seen

    # ----------------------------------------------------------- fusion
    def confidence(self, key):
        """0.0 on absent keys; -> 1.0 as evidence accumulates."""
        d = self.store.get(str(key).strip())
        if not d:
            return 0.0
        t = sum(d.values())
        return t / (t + self.C)

    def blend(self, key, probs):
        """Confidence-gated fusion into a model's output distribution.

        probs: {value: probability}. Absent key -> probs returned unchanged
        (the model speaks for itself). Present key -> the table's counts are
        mixed in with weight w = t/(t+C); at high counts the exact value
        dominates the softmax. This is how 'fused' recall is built:
        measured end-to-end earlier: bare 0/40, in-context 36/40, fused 40/40.
        """
        d = self.store.get(str(key).strip())
        if not d:
            return dict(probs)
        t = sum(d.values())
        w = t / (t + self.C)
        q = {v: p * (1.0 - w) for v, p in probs.items()}
        for v, c in d.items():
            q[v] = q.get(v, 0.0) + w * (c / t)
        return q

    # --------------------------------------------------------- identity
    def dumps(self):
        """Canonical serialization: sorted keys, fixed separators.
        Same facts -> same bytes, on any machine, any run."""
        return json.dumps(self.store, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)

    def sha(self):
        """Identity hash of the whole memory (first 16 hex chars)."""
        return hashlib.sha256(self.dumps().encode("utf-8")).hexdigest()[:16]

    def save(self, path=None):
        p = path or self.path or "life.json"
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(self.dumps())
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)  # atomic rename: a process crash never corrupts it
        return p

    def load(self, path=None):
        p = path or self.path or "life.json"
        with open(p, encoding="utf-8") as f:
            self.store = json.load(f)
        return self


# ------------------------------------------------------------------ CLI
def _cli(argv):
    args = list(argv)
    db = os.environ.get("LIFE_DB", "life.json")
    if "--db" in args:
        i = args.index("--db")
        db = args[i + 1]
        del args[i:i + 2]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    cmd, rest = args[0], args[1:]
    life = Life(db)

    if cmd == "put" and len(rest) == 2:
        life.learn(rest[0], rest[1])
        life.save(db)
        print("OK " + rest[0].strip())
    elif cmd == "get" and len(rest) == 1:
        v = life.recall(rest[0])
        print("ABSTAIN" if v is None else v)
        if v is None:
            return 3  # scripts can distinguish hit (0) from abstain (3)
    elif cmd == "history" and len(rest) == 1:
        h = life.history(rest[0])
        if not h:
            print("ABSTAIN")
            return 3
        for v, c in h:
            print(f"{c}\t{v}")
    elif cmd == "link" and len(rest) == 2:
        life.link(rest[0], rest[1])
        life.save(db)
        print(f"OK {rest[0].strip()} -> {rest[1].strip()}")
    elif cmd == "chain" and len(rest) == 1:
        print(" -> ".join(life.chain(rest[0])))
    elif cmd == "forget" and len(rest) == 1:
        gone = life.forget(rest[0])
        life.save(db)
        print("OK" if gone is not None else "ABSTAIN")
        if gone is None:
            return 3
    elif cmd == "stats":
        n = len(life.store)
        size = os.path.getsize(db) if os.path.exists(db) else 0
        print(f"keys {n} (incl. relation edges)  disk {size} B"
              + (f" ({size // n} B/key)" if n else "")
              + f"  sha {life.sha()}  db {db}")
    elif cmd == "sha":
        print(life.sha())
    elif cmd == "doctor":
        return _doctor(db, life)
    else:
        print(__doc__.strip())
        return 2
    return 0


def _doctor(db, life):
    """Is the Life actually fused here, and is it being used? A green/red
    checklist a creator runs in a project to KNOW, not hope."""
    import time
    ok = True

    def line(good, label, detail=""):
        nonlocal ok
        ok = ok and good
        print(f"  [{'OK ' if good else 'XX '}] {label}" + (f"  {detail}" if detail else ""))

    print("LIFE DOCTOR — is the memory wired and working here?")
    print("-" * 60)

    # 1. protocol installed where an agent will read it? (this is what makes
    #    fusion automatic — the ONLY thing that gates 'wired')
    proto = False
    for f in ("CLAUDE.md", "AGENTS.md"):
        if os.path.exists(f):
            with open(f, encoding="utf-8") as fh:
                if "LIFE-MEMORY BEGIN" in fh.read():
                    proto = True
                    line(True, f"protocol installed in {f}",
                         "-> Claude Code / Cursor here auto-use the Life")
    if not proto:
        line(False, "protocol in CLAUDE.md/AGENTS.md", "NOT found — run fuse.sh, "
             "or paste README §1 into your agent (required for claude.ai web)")

    # 2. the memory file — informational: is it being USED yet? (0 facts right
    #    after fusing is NORMAL, not a failure — it just hasn't been used.)
    n = len(life.store) if os.path.exists(db) else 0
    in_use = n > 0
    if os.path.exists(db):
        age = time.time() - os.path.getmtime(db)
        when = (f"{int(age)}s ago" if age < 90 else
                f"{int(age/60)}m ago" if age < 5400 else f"{int(age/3600)}h ago")
        print(f"  [{'OK ' if in_use else '.. '}] memory file {db}  "
              f"{n} facts, last written {when}")
        if in_use:
            k = next(iter(life.store))
            print(f"        newest-looking sample: {k!r} -> {life.recall(k)!r}")
        else:
            print("        (empty — not used yet; watch this count climb as the"
                  " agent stores facts. Not a fault.)")
    else:
        print(f"  [.. ] memory file {db}  none yet — no fact stored so far (normal"
              " before first use)")

    # 3. live round-trip: prove the mechanism itself works right now
    probe = "__doctor.probe__"
    life.learn(probe, "works")
    hit = life.recall(probe) == "works"
    miss = life.recall("__doctor.never__") is None
    life.forget(probe)
    line(hit and miss, "live round-trip",
         f"put/get verbatim={hit}, abstain-on-unknown={miss}")

    print("-" * 60)
    if ok and in_use:
        print("  RESULT: FUSED AND WORKING — wired, and already storing facts.")
    elif ok:
        print("  RESULT: WIRED, NOT YET USED — the agent here CAN use the Life;"
              " it just\n          hasn't stored a fact yet. Use it, then re-run"
              " doctor to see the count climb.")
    else:
        print("  RESULT: NOT WIRED — the protocol isn't installed, so an agent"
              " here won't\n          use the Life. Run fuse.sh (or paste README"
              " §1). See the XX line above.")
    print("  Prove it end-to-end: put a fact, quit, and in a NEW session"
          " `get` it back\n  verbatim — and `get` a key you never stored to see"
          " ABSTAIN.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
