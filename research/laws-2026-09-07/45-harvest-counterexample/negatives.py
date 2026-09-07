"""PROTOTYPE (report-only; src/ is not edited).

The engine law's HARVEST_COUNTEREXAMPLE act, actuated as a MEMORY instead of
a report: every rejected candidate is kept as a NEGATIVE and consulted before
the same candidate is proposed again.

Today (measured, see REPORT.md):
  * loop.py:346/407 harvest rejections into RepairResult.tried_log, capped at
    64 per repair() call, candidate text truncated to 200 chars;
  * guard.py:719 persists report.attempts[:200] to .fluidfix/last_refusal.json;
  * NOTHING under src/ ever reads either back. loop.py:185 scopes the dedupe
    set `tried` to ONE repair() call, so the escalation pass inside a single
    guard run, and every later guard run, re-propose candidates already known
    to leave the suite red.

This module installs the read-back, without touching src/, by wrapping the
`candidates` name that loop.py imported.

SOUNDNESS. A candidate is skipped only when
    (same file, same edit site, same candidate text, same TREE FINGERPRINT)
where the fingerprint is a content hash of every source file in the repo. A
rejection is a fact about the tree it was measured against; change any byte of
the tree and the fingerprint changes and every negative is re-tried. So the
memo can never turn a repair into a refusal on a tree that differs from the
one the rejection was measured on, and on an IDENTICAL tree the suite verdict
it replays is the verdict the suite just gave.
"""
from __future__ import annotations

import hashlib
import json
import os

SRC_EXT = (".py", ".c", ".h", ".java", ".cpp", ".hpp", ".cc")
SKIP_DIR = {".git", ".fluidfix", "__pycache__", ".pytest_cache", ".venv"}


def tree_fingerprint(root: str) -> str:
    """Content hash of the repo's source tree. A negative is only valid
    against the tree it was measured on."""
    h = hashlib.sha1()
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIR)
        for f in sorted(fn):
            if not f.endswith(SRC_EXT):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            try:
                b = open(p, "rb").read()
            except OSError:
                continue
            h.update(rel.encode()); h.update(hashlib.sha1(b).digest())
    return h.hexdigest()


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


def key_for(obs, cand) -> tuple[str, str]:
    """(edit site, candidate hash) — the identity of one tried candidate."""
    start = getattr(cand, "start", None)
    if start is not None:                       # SpanEdit
        return (f"{obs.file}:{cand.start}-{cand.end}", _sha(cand.text))
    return (f"{obs.file}:{obs.lineno}", _sha(cand))


class Negatives:
    """The store. `path` persists it across processes, exactly where
    .fluidfix/last_refusal.json already lives."""

    def __init__(self, path: str | None = None):
        self.path = path
        self.entries: dict[str, dict] = {}
        if path and os.path.exists(path):
            try:
                self.entries = json.load(open(path))["negatives"]
            except Exception:
                self.entries = {}
        # per-run instrumentation
        self.skipped = 0
        self.yielded: list[tuple[str, str, str]] = []   # (at, sha, text)
        self.skipped_at: list[str] = []

    # -------------------------------------------------------------- store --
    @staticmethod
    def _k(at: str, sha: str, fp: str) -> str:
        return f"{fp}|{at}|{sha}"

    def known(self, at: str, sha: str, fp: str) -> bool:
        return self._k(at, sha, fp) in self.entries

    def add(self, at: str, sha: str, fp: str, why: str = "") -> None:
        self.entries[self._k(at, sha, fp)] = {"at": at, "why": why[:400]}

    def save(self) -> None:
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            json.dump({"negatives": self.entries}, open(self.path, "w"), indent=1)

    # ------------------------------------------------------------- wiring --
    def install(self, fingerprint: str):
        """Wrap the `candidates` name loop.py imported. Returns an uninstall
        callable. No file under src/ is modified."""
        from fluidfix import loop as _loop
        real = _loop.candidates
        self.skipped = 0
        self.yielded = []
        self.skipped_at = []

        def patched(line, act, obs):
            out = real(line, act, obs)
            kept = []
            for c in out:
                at, sha = key_for(obs, c)
                if self.known(at, sha, fingerprint):
                    self.skipped += 1
                    self.skipped_at.append(at)
                    continue
                text = getattr(c, "text", c)
                self.yielded.append((at, sha, text))
                # PROVISIONAL add, so a later repair() call in the SAME run
                # (the escalation pass) already sees it. Safe: the only
                # candidate that must not be skipped is a green one, and a
                # repair() call that finds a green returns a terminal result
                # that ends the whole guard pass — it is never re-proposed.
                # harvest() removes any green again before the store is saved.
                self.add(at, sha, fingerprint)
                kept.append(c)
            return kept

        _loop.candidates = patched
        return lambda: setattr(_loop, "candidates", real)

    def harvest(self, fingerprint: str, green_texts=()) -> int:
        """Everything proposed this run that was NOT green is a negative.

        loop.py processes every candidate it is handed (deadlines are only
        checked BETWEEN kinds and observations, never inside a candidate set),
        so "was yielded" implies "was adjudicated or was a NOPROGRESS/dup
        no-op" — either way it is known not to be the repair on this tree."""
        green = set(green_texts)
        n = 0
        for at, sha, text in self.yielded:
            if text in green:                 # a green is NOT a negative
                self.entries.pop(self._k(at, sha, fingerprint), None)
                continue
            self.add(at, sha, fingerprint)
            n += 1
        return n


class Counter:
    """MEASURED cost: candidate adjudications and real pytest invocations."""

    def __init__(self, oracle):
        self.oracle = oracle
        self.check = 0
        self.pytest = 0
        _check, _run = oracle.check, oracle.run

        def check_(timeout=None):
            self.check += 1
            return _check(timeout=timeout)

        def run_(args, cache=False, timeout=None):
            self.pytest += 1
            return _run(args, cache=cache, timeout=timeout)

        oracle.check = check_
        oracle.run = run_

    def reset(self):
        self.check = self.pytest = 0
