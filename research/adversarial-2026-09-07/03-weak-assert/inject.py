#!/usr/bin/env python
"""Enumerate every in-vocabulary single-line defect of the victim library.

The injector uses FLUIDFIX'S OWN act appliers, so every defect it produces is
by construction inside the vocabulary fluidfix claims to repair -- no
strawman mutants. Output: defects.json, a list of
    {"id", "lineno", "kind", "act", "orig", "mutant"}
"""
import json
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import KINDS, Observation, act_for, candidates  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VICTIM = os.environ.get("VICTIM", "victim")
PKG = os.environ.get("PKG", "weakpkg")
SRC = os.path.join(HERE, VICTIM, PKG, "core.py")


def main():
    src = open(SRC, encoding="utf-8", newline="").read()
    raw = src.split("\n")
    out = []
    seen = set()
    for i, line in enumerate(raw):
        body = line.rstrip("\r")
        if not body.strip() or body.lstrip().startswith(("#", '"""')):
            continue
        for kind, (name, _desc, sig) in sorted(KINDS.items()):
            if not sig.search(body):
                continue
            act = act_for(kind)
            obs = Observation(lineno=i + 1, kinds=[kind])
            obs.file, obs.root = f"{PKG}/core.py", os.path.join(HERE, VICTIM)
            obs.all_lines = [l.rstrip("\r") for l in raw]
            for cand in candidates(body, act, obs):
                if not isinstance(cand, str) or cand == body:
                    continue
                key = (i + 1, cand)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"id": len(out), "lineno": i + 1, "kind": kind,
                            "kind_name": name, "act": act,
                            "orig": body, "mutant": cand})
    with open(os.path.join(HERE, os.environ.get("DEFECTS", "defects.json")), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out)} candidate defects enumerated")


if __name__ == "__main__":
    main()
